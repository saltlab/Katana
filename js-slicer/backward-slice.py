import understand
import traceback
import csv
import json
import sys
import os
from difflib import get_close_matches, ndiff
import concurrent.futures

csv.field_size_limit(sys.maxsize)
REL_KIND = ['web Javascript Definein', 'web Javascript Setby', 'web Javascript Modifyby']


def safe_list_get(arr, idx):
  try:
    return arr[idx]
  except IndexError:
    return None


def get_patch_from_diff(diff):
  buggy_line = None
  fixed_line = None
  for line in diff.split('\n'):
    if line.startswith('-'):
        buggy_line = line.lstrip('-')
    elif line.startswith('+'):
        fixed_line = line.lstrip('+')
  return buggy_line, fixed_line


class BackwardSlicing(object):
  def __init__(self, db, file, buggy_line_num) -> None:
      self.file = file
      self.db = db
      self.buggy_line_num = buggy_line_num
      self.method_lines = []
      self.loops = {}
      self.conds = {}
      self.conditional_scope = {}
      self.statement_closure = {}
      self.scope = {}
      self.method_start_line_num = -1
      self.function_variables = []
      self.has_function_call = False
      self.else_lines = set()

      for lexeme in file.lexer():
        if lexeme.line_begin() == buggy_line_num:
          if lexeme.token() == 'Identifier' and lexeme.ent() and lexeme.ent().parent() and lexeme.ent().parent().kindname() in ['Function', 'Class', 'File']:
            lines = set()
            for ref in lexeme.ent().parent().refs():
              if not self.method_start_line_num:
                self.method_start_line_num = ref.line()
              if ref.kind().longname() not in ['web Javascript Callby Nondynamic', 'web Javascript Useby', 'web Javascript Useby Deref Partial']:
                lines.add(ref.line())
            self.method_lines = sorted(lines)
            break

  
  def _get_outermost_parent(self, first_line):
      for lexeme in self.file.lexer():
        if lexeme.line_begin() == first_line and lexeme.token() not in ['Whitespace', 'Newline']:
          if lexeme.ent() and lexeme.ent().parent():
            if lexeme.ent().parent().kindname() == 'File':
              return None
            elif lexeme.ent().parent().kindname() != 'File':
              return lexeme.ent().parent().refs()[0].line()
          return None


  # For cases when the . goes to next line, for example,
  # array
  #  .find(a => a !== 2)
  #  .map(a => a + 1)
  def _get_object_beginning(self, line_number):
      for lexeme in self.file.lexer():
        if lexeme.line_begin() == line_number:
          if lexeme.token() not in ['Whitespace', 'Newline']:
            if lexeme.text() == '.' and lexeme.previous().token() == 'Whitespace':
              return self._get_object_beginning(line_number - 1)
            else:
              return line_number 


  # Find all variables in the line
  def get_variable_entities(self, line_number):
      variables = []
      for lexeme in self.file.lexer():
        if lexeme.line_begin() == line_number:
          if lexeme.token() == 'Identifier' and lexeme.ent():
            variables.append(lexeme.ent())
          if lexeme.ent() and lexeme.ent().kindname() == 'Property':
            variables.append(lexeme.ent().parent())

      return variables
  

  def is_within_loop(self, line_num):
    loop_lines = []
    for i in self.loops.items():
      if i[1].get('line_num_begin') and i[1].get('line_num_end') and line_num:
        if line_num >= int(i[1]['line_num_begin']) and line_num <= int(i[1]['line_num_end']): 
          loop_lines.append((i[1]['line_num_begin'], i[1]['line_num_end']))
    return loop_lines

  def is_within_scope(self, line_num):
    scope_lines = []
    for i in self.scope.items():
      if i[1].get('line_num_begin') and i[1].get('line_num_end') and line_num:
        if line_num >= int(i[1]['line_num_begin']) and line_num <= int(i[1]['line_num_end']):
          scope_lines.append((i[1]['line_num_begin'], i[1]['line_num_end'], i[1]['is_variable']))
    return scope_lines

  def is_within_conditional(self, line_num):
    cond_lines = []
    for i in self.conds.items():
      if i[1].get('line_num_begin') and i[1].get('line_num_end') and line_num:
        if line_num >= int(i[1]['line_num_begin']) and line_num <= int(i[1]['line_num_end']): 
          cond_lines.append((i[1]['line_num_begin'], i[1]['line_num_end']))
          if 'else' in i[0]:
            self.else_lines.add(i[1]['line_num_begin'])
    return cond_lines

  def find_conditional_by_else(self, lines):
    updated_lines = lines.copy()
    common_lines_between_current_and_else_lines = self.else_lines.intersection(lines)
    for line_num in common_lines_between_current_and_else_lines:
      for cond_type_line_map in self.conditional_scope.values():
        if 'else' in cond_type_line_map:
          last_index = len(cond_type_line_map['else']) - 1
          for idx, val in enumerate(cond_type_line_map['else']):
            if val['line_num_begin'] == line_num:
              start_if = cond_type_line_map['if']['line_num_begin']
              if start_if not in lines:
                c = start_if
                while c < line_num:
                  updated_lines.add(c)
                  c += 1
              if idx == last_index and cond_type_line_map.get('endif'):
                updated_lines.add(cond_type_line_map['endif']['line_num_begin'])

    return updated_lines


  def on_add_line(self, line_numbers):
    def _on_add(line_num):
      is_within_loop = self.is_within_loop(line_num)
      is_within_conditional = self.is_within_conditional(line_num)
      is_within_scope = self.is_within_scope(line_num)
      new_lines = set()

      if len(is_within_loop): # if a line is start of the loop, add the end of the loop (curly brace)
        for l in is_within_loop:
          new_lines.add(l[0])
          new_lines.add(l[1])
      if len(is_within_conditional): # if a line is start of the loop, add the end of the loop (curly brace)
        for l in is_within_conditional:
          new_lines.add(l[0])
          new_lines.add(l[1])
      if len(is_within_scope): # if a line is start of the scope, add the end of the scope (curly brace)
        for l in is_within_scope:
          new_lines.add(l[0])
          i = l[0]
          if l[2]:
            while i <= l[1]:
              new_lines.add(i)
              i += 1
          else:
            new_lines.add(l[1])
      return new_lines
    
    if type(line_numbers) is set:
      updated_set = set()
      for l in line_numbers:
        updated_set = _on_add(l).union(updated_set)
      return updated_set
    else:
      return _on_add(line_numbers)

    
  def get_statements(self, lines):
      statements = []
      line_to_col_map = {} # stores the lines where some parts of the line needs to be included (not the whole line)
      updated_lines = lines.copy()

      for line_num in lines:
        key = str(line_num)

        if self.has_function_call and line_num in self.function_variables: # for variables that are function calls, get the whole scope of the function
          if key in self.scope and self.scope[key] is not None:
            i = line_num
            while i < self.scope[key].get('line_num_begin'):
              updated_lines.add(i)
              i += 1
        
        updated_lines = self.on_add_line(line_num).union(updated_lines)

        if key in self.conds and self.conds[key]['line_num_end']: # if a line is start of a conditional, add the end of the loop (curly brace)
          line = self.conds[key]['line_num_end']
          updated_lines.add(line)
          if self.conds[key].get('column_num_begin') and line not in line_to_col_map: # this takes care of the column end
            line_to_col_map[line] = {
              'column_num_begin': self.conds[key]['column_num_begin'],
              'column_num_end': self.conds[key]['column_num_end']
            }
        if key in self.scope and self.scope[key] is not None and 'line_num_end' in self.scope[key]: # if a line falls within a method scope, add the end of the line to the list
          line = self.scope[key]['line_num_end']
          updated_lines.add(line)
          if self.scope[key].get('column_num_begin') and self.scope[key].get('column_num_end') and line not in line_to_col_map: # this takes care of the column end
            line_to_col_map[line] = {
              'column_num_begin': self.scope[key]['column_num_begin'],
              'column_num_end': self.scope[key]['column_num_end']
            }
          updated_lines.add(self.scope[key]['line_num_end'])  
        
        # check if the lines fall within an if block, then add the else blocks too
        for i in self.conds:
          block_start = int(i.split('_')[-1]) if i.startswith('else_') else int(i)
          if int(line_num) >= block_start and int(line_num) <= int(self.conds[i]['line_num_end']):
            updated_lines.add(block_start)
            updated_lines.add(self.conds[i]['line_num_end'])
            if self.conds[i].get('column_num_end'):
              if block_start in line_to_col_map:
                del line_to_col_map[block_start]
              else:
                line_to_col_map[self.conds[i]['line_num_end']] = {
                  'column_num_begin': self.conds[i]['column_num_begin'],
                  'column_num_end': self.conds[i]['column_num_end']
                }
  
        # this takes care of single line statement end
        for statement_continuations in self.statement_closure.values():
          if line_num in statement_continuations:
            for s in statement_continuations:
              updated_lines.add(s)
              updated_lines = self.on_add_line(s).union(updated_lines)


      updated_lines = set(sorted([i for i in updated_lines if i]))
      if int(self.method_start_line_num) in updated_lines:
        updated_lines.add(self.method_lines[-1])
        updated_lines = self.on_add_line(self.method_lines[-1]).union(updated_lines)

      # this takes care of object start
      start_of_line = None
      for line_num in list(updated_lines.copy()):
        for lexeme in self.file.lexer():
          if lexeme.line_begin() == line_num:
            if lexeme.text() == '.' and lexeme.previous().token() == 'Whitespace':
              start_of_line = self._get_object_beginning(line_num - 1)

              if start_of_line:
                updated_lines.add(start_of_line)
                updated_lines = self.on_add_line(start_of_line).union(updated_lines)
                start_of_line = None
      
      parent_line = self._get_outermost_parent(min(updated_lines))
      if parent_line and self.scope.get(str(parent_line)):
        updated_lines.add(parent_line)
        end_line = self.scope[str(parent_line)].get('line_num_end')
        if end_line:
          updated_lines.add(end_line)

      lines_with_related_vars = self.get_related_var_lines(set(updated_lines), set(updated_lines), show_use_by=True)
      
      unified_lines = self.on_add_line(lines_with_related_vars.difference(updated_lines)).union(lines_with_related_vars)
      final_lines = self.find_conditional_by_else(unified_lines)
      updated_lines = sorted([i for i in final_lines if i])

      for line_num in updated_lines:
        statement = ''
        for lexeme in self.file.lexer():
          if lexeme.line_begin() == line_num:
            if lexeme.token() not in ['Newline']:
              if line_num in line_to_col_map:
                if lexeme.column_end() <= line_to_col_map[line_num]['column_num_end']:
                  statement += lexeme.text()
              else:
                statement += lexeme.text()

        statements.append(statement.rstrip())

      return statements    
  

  def analyze_closure(self):
      self._record_scope()
      self._record_conditional_scope()
      for line_num in self.method_lines:
        for lexeme in self.file.lexer():
          if lexeme.line_begin() == line_num:
            if lexeme.token() not in ['Whitespace', 'Newline']:
              if lexeme.token() == 'Keyword' and lexeme.text() in ['for', 'while']:
                self._record_loop_closure(lexeme, line_num)
              elif lexeme.text() == 'if':
                self._record_if_closure(lexeme, line_num)
                self._record_else_closure(lexeme)
            self._record_line_closure(lexeme, line_num)


  def _record_line_closure(self, lexeme, line_num):
      line_key = str(line_num)
      if line_key not in self.statement_closure:
        self.statement_closure[line_key] = []
        while lexeme and lexeme.line_begin() < (self.method_lines[-1] + 1) and lexeme.line_begin() > self.method_lines[0]:
          if lexeme.text() in ['{', '}', 'if', 'else', 'while', 'try', 'catch'] and lexeme.line_begin() == line_num:
            del self.statement_closure[line_key]
            break

          if lexeme.text() == ';':
            self.statement_closure[line_key] = list(range(line_num, lexeme.line_begin() + 1))
            break
          lexeme = lexeme.next()
  

  def _record_scope(self):
      brace_map = { '{': '}', '[': ']', '(': ')' }
      stack = []
      line_stack = []
      is_variable = {}
      for lexeme in self.file.lexer():
        line_key = str(lexeme.line_begin())
        if lexeme.token() == 'Keyword' and lexeme.text() == 'function':
            self.function_variables.append(lexeme.line_begin())
        if lexeme.ent() and lexeme.ent().kindname() == 'Variable' and lexeme.ent().type() in ['{}', '[{}]', '[]']:
          is_variable[line_key] = True
        if lexeme.text() in ['{', '(', '[']:
            stack.append(lexeme.text())
            line_stack.append(line_key)
            self.scope[line_key] = {
              'is_variable': is_variable.get(line_key, False),
              'line_num_begin': lexeme.line_begin(),
              'column_num_begin': lexeme.column_begin(),
            }

        elif lexeme.text() in ['}', ']', ')']:
          if stack and brace_map[stack[-1]] == lexeme.text():
              self.scope[line_stack[-1]]['line_num_end'] = lexeme.line_begin()
              if lexeme.next() and lexeme.next().next() and lexeme.next().token() == 'Newline' and lexeme.next().next().token() != 'Indent':
                self.scope[line_stack[-1]]['column_num_end'] = lexeme.column_end()

              stack.pop()
              line_stack.pop()

  
  def _record_loop_closure(self, lexeme, line_num):
      loop_key = str(line_num)
      self.loops[loop_key] = {
        'line_num_begin': line_num,
        'line_num_end': line_num,
        'enclosing_brace_count': 0
      }
      while lexeme and lexeme.line_begin() < self.method_lines[-1]:
        if lexeme.text() == '{':
          self.loops[loop_key]['enclosing_brace_count'] += 1
        if lexeme.text() == '}' and self.loops[loop_key]['enclosing_brace_count'] > 0:
          self.loops[loop_key]['enclosing_brace_count'] -= 1
          if self.loops[loop_key]['enclosing_brace_count'] == 0:
            self.loops[loop_key]['line_num_end'] = lexeme.line_begin()
            break
        lexeme = lexeme.next()


  def _record_conditional_scope(self):
      if_tracker_stack = []
      self.conditional_scope = {}
      else_if_tracker = []
      curr_if = []

      if self.parent_type == 'File':
        for entity in self.db.ents('file'):
          if str(self.file) in str(entity):
            self.extract_control_flow(entity)


      for lexeme in self.file.lexer():
        if lexeme.token() not in ['Whitespace', 'Newline']:
          if not lexeme.ent():
            continue
          control_flow_graph = lexeme.ent().freetext('CGraph')

          if self.parent_type == 'Function':
            self.extract_control_flow(lexeme.ent())

          if control_flow_graph:
            for parser in control_flow_graph.split(';'):
              parser_nums = []
              for x in parser.split(','): # node_type, start_line, start_col, end_line, end_col
                if x != '':
                  try:
                    parser_nums.append(int(x))
                  except ValueError:
                    parser_nums = []
                    break
              if not parser_nums or len(parser_nums) < 5:
                continue
              if parser_nums[0] == 5:
                if parser_nums[1] not in else_if_tracker:
                  if_tracker_stack.append(parser_nums)
                  curr_if.append(parser_nums)
                  self.conditional_scope[parser_nums[1]] = {
                    'if': {
                      'line_num_begin': parser_nums[1],
                      'column_num_begin': parser_nums[2],
                      'line_num_end': parser_nums[3],
                      'column_num_end': parser_nums[4]
                    }
                  }
              elif parser_nums[0] == 7 and (len(if_tracker_stack) or curr_if): # 7 = else, 8 = endif
                if not len(curr_if):
                  curr_if.append(if_tracker_stack[-1])
                else_if_tracker.append(parser_nums[1])
                current = curr_if.pop()
                if 'else' not in self.conditional_scope[current[1]]:
                  self.conditional_scope[current[1]]['else'] = [{
                    'line_num_begin': parser_nums[1],
                    'column_num_begin': parser_nums[2],
                    'line_num_end': parser_nums[3],
                    'column_num_end': parser_nums[4]
                  }]
                else:
                  self.conditional_scope[current[1]]['else'].append({
                    'line_num_begin': parser_nums[1],
                    'column_num_begin': parser_nums[2],
                    'line_num_end': parser_nums[3],
                    'column_num_end': parser_nums[4]
                  })
              elif parser_nums[0] == 8 and (len(curr_if)):
                current = curr_if.pop()
                self.conditional_scope[current[1]]['endif'] = {
                  'line_num_begin': parser_nums[1],
                  'column_num_begin': parser_nums[2],
                  'line_num_end': parser_nums[3],
                  'column_num_end': parser_nums[4]
                }
                if len(if_tracker_stack):
                  if_tracker_stack.pop()

  def _lexeme_matcher(self, lexeme, string, line_num, direction='next'):
      while lexeme:
        if lexeme.line_begin() == line_num:
          if lexeme.text() == string:
            return True
        else:
          return False

        if direction == 'next':
          lexeme = lexeme.next()
        else:
          lexeme = lexeme.previous()

  def _get_matched_lexeme(self, type, lexeme, string, line_num, direction='next'):
      matcher = lexeme.text() == string if type == 'string' else lexeme.token() == string
      while lexeme:
        if lexeme.line_begin() == line_num:
          if matcher:
            return lexeme
        else:
          return None

        if direction == 'next':
          lexeme = lexeme.next()
        else:
          lexeme = lexeme.previous()


  def _record_if_closure(self, lexeme, line_num):
      cond_key = str(line_num)
      self.conds[cond_key] = {
        'line_num_begin': line_num,
        'line_num_end': line_num,
        'column_num_begin': lexeme.column_begin(),
        'column_num_end': lexeme.column_begin(),
        'enclosing_brace_count': 0,
      }

      if_without_braces = False
      has_braces = False
      while lexeme and lexeme.line_begin() < self.method_lines[-1]:
        if lexeme.token() == 'Newline' and self._lexeme_matcher(lexeme, ')', lexeme.line_begin(), 'previous') and not has_braces:
          if_without_braces = True
          has_braces = False
        if if_without_braces and lexeme.text() == ';':
          self.conds[cond_key]['has_braces'] = False
          self.conds[cond_key]['line_num_end'] = lexeme.line_begin()
          self.conds[cond_key]['column_num_end'] = lexeme.column_end()
          break
        if lexeme.text() == '{' and not if_without_braces:
          has_braces = True
          self.conds[cond_key]['enclosing_brace_count'] += 1
          self.conds[cond_key]['has_braces'] = True
        if lexeme.text() == '}' and self.conds[cond_key]['enclosing_brace_count'] > 0 and not if_without_braces:
          self.conds[cond_key]['enclosing_brace_count'] -= 1
          if self.conds[cond_key]['enclosing_brace_count'] == 0:
            self.conds[cond_key]['line_num_end'] = lexeme.line_begin()
            self.conds[cond_key]['column_num_end'] = lexeme.column_end()
            break

        lexeme = lexeme.next()

    
  def _record_else_closure(self, lexeme):
    while lexeme and lexeme.line_begin() < self.method_lines[-1]:
      if lexeme.text() == 'else':
        else_key = lexeme.text() + '_' + str(lexeme.line_begin())
        lex_it = lexeme
        self.conds[else_key] = {}
        self.conds[else_key] = {
          'column_num_begin': lexeme.column_begin(),
          'column_num_end': lexeme.column_end(),
          'line_num_begin': lexeme.line_begin()
        }

        else_without_braces = False
        has_braces = False
        while lex_it and lex_it.line_begin() < self.method_lines[-1]:
          if lex_it.token() != 'Whitespace':
            if lex_it.text() == '{' and lex_it.previous().text() != '$':
              has_braces = True
              self.conds[else_key]['has_braces'] = True
              else_without_braces = False

            if lex_it.token() == 'Newline' and not has_braces:
              else_without_braces = True
              self.conds[else_key]['has_braces'] = False
              matched_lexeme = self._get_matched_lexeme('string', lex_it.next(), ';', lex_it.line_end() + 1) or self._get_matched_lexeme('token', lex_it.next(), 'Newline', lex_it.line_end() + 1)
              if matched_lexeme:
                self.conds[else_key]['column_num_end'] = matched_lexeme.column_end() 
                self.conds[else_key]['line_num_end'] = lex_it.line_end() + 1
                break
              lex_it = lex_it.next()
              
            if else_without_braces and (lex_it.text() == ';' or (lex_it.next() and lex_it.next().token() == 'Newline')):
              self.conds[else_key]['column_num_end'] = lex_it.column_end() + 1
              self.conds[else_key]['line_num_end'] = lex_it.line_end()
              else_without_braces = False
              self.conds[else_key]['has_braces'] = False
              break

            if lex_it.text() == '}' and lex_it.next().text() != '`' and not else_without_braces:
              self.conds[else_key]['column_num_end'] = lex_it.column_end()
              self.conds[else_key]['line_num_end'] = lex_it.line_end()
              break

            self.conds[else_key]['column_num_end'] = lex_it.column_end()
            self.conds[else_key]['line_num_end'] = lex_it.line_end()

          lex_it = lex_it.next()      
      lexeme = lexeme.next()


  def _record_class_scope(self, lexeme, line_stack):
    while lexeme:
      if lexeme.text() == 'class':
        line_stack.add(lexeme.line_begin())
        break
      lexeme = lexeme.previous()

  
  def _record_method_scope(self, lexeme, line_stack):
    builder = []
    while lexeme:
      if lexeme.text() in ['{', ')']:
        builder.append(lexeme.text())
      
      if (' '.join(builder) == ') {'):
        line_stack.add(lexeme.line_begin())
        break
      lexeme = lexeme.previous()


  def _record_object_scope(self, lexeme, line_stack):
    while lexeme:
      if lexeme.text() == '{':
        line_stack.add(lexeme.line_begin())
        break
      lexeme = lexeme.previous()


  def get_related_var_lines(self, line_stack, analyzed_lines, show_use_by=False):
    pointer_line = next(iter(line_stack))
    variables = self.get_variable_entities(pointer_line)

    while len(line_stack) > 0:
      for var in variables:
        for reference in var.refs():
          current_line = reference.line()
          if current_line <= self.buggy_line_num and current_line not in analyzed_lines and reference.kind().longname() in REL_KIND:
            line_stack.add(current_line)

      analyzed_lines.add(pointer_line)
      line_stack.remove(pointer_line)
      if len(line_stack) > 0:
        pointer_line = next(iter(line_stack))
        variables = self.get_variable_entities(pointer_line)
    return analyzed_lines


  def run(self, file_obj=None, root_path=None, dual_slice=False, js_file_type=None):
      line_stack = set()
      analyzed_lines = set()
      variables = self.get_variable_entities(self.buggy_line_num)

      for var in variables:
        if var.kindname() == 'Function':
          self.has_function_call = True
        if var.parent() and (var.parent().name() == 'constructor' or var.parent().kindname() == 'Function'): # If its a function within a class, record the parent scope
          lexeme = var.lexer().lexeme(var.ref().line(), var.ref().column())
          self._record_class_scope(lexeme, line_stack)
          self._record_method_scope(lexeme, line_stack)
        for reference in var.refs():
          current_line = reference.line()
          if current_line < self.buggy_line_num and current_line > self.method_start_line_num and current_line not in analyzed_lines and reference.kind().longname() in REL_KIND:
            line_stack.add(current_line)
      
      analyzed_lines.add(self.buggy_line_num)

      if not len(line_stack):
        return 'No lines'

      analyzed_lines = self.get_related_var_lines(line_stack, analyzed_lines)

      self.analyze_closure()
      statements = self.get_statements(set([a for a in analyzed_lines if a is not None]))

      if file_obj and file_obj['buggy_line'] and len(statements):
        if not dual_slice:
          print('Writing slice to files......')
          buggy_file = open(root_path + file_obj['buggy_file'], "w")
          fixed_file = open(root_path + file_obj['fixed_file'], "w")
          closest_match = get_close_matches(file_obj['buggy_line'], statements, n=1)
          if len(closest_match):
            last_occurence_of_buggy_line = len(statements) - statements[::-1].index(closest_match[0]) - 1
            if last_occurence_of_buggy_line > -1:
              for idx, s in enumerate(statements):
                buggy_file.write(s+'\n')
                if s in closest_match and idx == last_occurence_of_buggy_line:
                  fixed_file.write(file_obj['fixed_line']+'\n') 
                else:
                  fixed_file.write(s+'\n') 

              buggy_file.close()
              fixed_file.close()
              return statements
        else:
          print('Writing dual slice to files for file type {}......'.format(js_file_type))
          js_file = open(root_path + file_obj[js_file_type], "w")
          for s in statements:
            js_file.write(s+'\n')
          js_file.close()
          return statements
      else:
        print('********* Sliced Statements **********')
        [print(s) for s in statements]
        print('********* End **********')
        return statements


def process_single_file(project_path):
  db = understand.open(project_path)
  
  buggy_line_num = 9
  file = db.lookup("test.js")[0]
  bs = BackwardSlicing(db, file, buggy_line_num)
  bs.run()


def test_backward_slice():
  db = understand.open('./test-slice-js/test-slice-js.und')
  with open('./test-slice-js/file_line_map.json') as f:
    file_line_map = json.load(f)
    for item in file_line_map:
      file = db.lookup(item['file'])[0]
      bs = BackwardSlicing(db, file, item['line_num'])
      actual_statements = bs.run()
      actual_statements = ''.join([s.strip() for s in actual_statements])

      if item['expected_output']:
        assert actual_statements == item['expected_output'], 'Failed assertion in {} {}'.format(item['file'], item['line_num'])
        print('TEST PASSED for file/line', item['file'], item['line_num'])
      else:
        print('ACTUAL --- ', actual_statements)


def is_whitespace_diff(buggy_line, fixed_line):
  output_list = [li for li in ndiff(fixed_line, buggy_line) if li[0] != ' ']
  if len(output_list):
    return all(f.strip() in ['+', '-'] for f in output_list)
  return False


def process_split_projects(project_path, root_sliced_path, dual_slice):
  subdir = project_path.split('/')[-1]

  udb = '{}/{}.und'.format(project_path, subdir)
  folderpath_db_map = {}
  folderpath_db_map[udb] = project_path
  
  files = []
  csv_file_path = project_path + '/' + '{}_bugs_info.csv'.format(subdir)

  with open(csv_file_path) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')

    for row in csv_reader:
      files.append({
				'buggy_line_num': row[2],
				'buggy_line': row[3],
				'fixed_line': row[4],
				'buggy_file': row[0],
				'fixed_file': row[1]
			})


  def generate_slice(row):
    buggy_file = row['buggy_file']
    fixed_file = row['fixed_file']
    buggy_line_num = row['buggy_line_num']

    if os.path.exists(root_sliced_path + buggy_file):
      print('File already exists ---- Skipping...')
      return ''
    elif (os.path.exists(folderpath_db_map[udb] + '/' + buggy_file) and os.path.exists(folderpath_db_map[udb] + '/' + fixed_file)):
      print('Processing buggy file -----', buggy_file, buggy_line_num)
      file_obj = {
        'buggy_line': row['buggy_line'],
        'fixed_line': row['fixed_line'],
        'buggy_file': buggy_file,
        'fixed_file': fixed_file
      }
      try:
        db_file = db.lookup(buggy_file, 'File')
        if db_file:
          buggy_file_slice = BackwardSlicing(db, db_file[0], int(buggy_line_num))
          print('Doing backward slice on buggy file {}......'.format(buggy_file))
          try:
            buggy_file_slice.run(file_obj, root_path=root_sliced_path, dual_slice=dual_slice, js_file_type='buggy_file')
          except Exception as err:
            print('Error in file', buggy_file, err)
            traceback.print_exc()
      except SystemError:
        return ''
      
      if dual_slice:
        try:
          db_file = db.lookup(fixed_file, 'File')
          if db_file:
            fixed_file_slice = BackwardSlicing(db, db_file[0], int(buggy_line_num))
            print('Doing backward slice on fixed file {}......'.format(fixed_file))
            try:
              fixed_file_slice.run(file_obj, root_path=root_sliced_path, dual_slice=dual_slice, js_file_type='fixed_file')
              return 'Success'
            except Exception as err:
              print('Error in file', fixed_file, err)
              traceback.print_exc()
        except SystemError:
          return ''
      
      return 'Success'

  db = understand.open(udb)

  with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = []
    print('Accessing udb.....', udb)
    for row in files:
      futures.append(executor.submit(generate_slice, row))
    for future in concurrent.futures.as_completed(futures):
      print(future.result())

  print('********** DONE **********')


if __name__ == '__main__':
    project_type = sys.argv[1] or 'test' # choices = ['single', 'multiple', 'test']
    dual_slice = False if sys.argv[2] == 'False' else True
    project_path = sys.argv[3:]

    if project_type == 'multiple':
      for dir in project_path:
        print('Slicing for folder {}'.format(dir))
        root_sliced_path = '{}/{}/'.format(dir, 'sliced_dual' if dual_slice else 'sliced')
        try:
          os.mkdir(root_sliced_path)
        except FileExistsError:
          print('Folder exists..')
        process_split_projects(dir, root_sliced_path, dual_slice)
        print('Completed slicing for folder {}'.format(dir))
    elif project_type == 'single':
      process_single_file(project_path[0])
    else:
      test_backward_slice() # For testing slicing stability
