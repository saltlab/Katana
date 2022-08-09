function removeHtmlMarkup(s) {
  let tag = false;
  let quote = false;
  let out = '';
  let a = 3;
  
  for (let c of s) {
    for (let i = 0; i < 5; i++) {
      if (c === '<' && !quote) {
        tag = true;
      } else if (c === '>' && !quote) {
        tag = false; // slice
      } else if (c === '"' || c === "'" && tag) {
        quote = !quote; // slice
      } else if (!tag) {
        out = out + c;
      } else {
        tag = out + quote; //slice
      }
    }
  }
  
  console.assert(out.includes('<') === -1);
  return out;
}


function getExamGrade(marks, threshold) {
  marks = marks / threshold;
  if (marks > 95)
    return "Grade: A+ with marks" + marks;
  else if (marks < 94 && marks > 80)
    return "Grade: A with marks" + marks;
  else if (marks < 80 && marks > 70) // slice
    return "Grade: B with marks" + marks;
  else if (marks < 70 && marks > 60)
    return "Grade: C with marks" + marks;
  else
    return "Grade: F with marks" + marks;
}

function getExamGradeWithThreshold(marks, threshold) {
  marks = marks / threshold;
  if (marks > 95) {
    if (marks + threshold > 100) 
      return marks + ' 100';
    else
      return `Grade: A+ with marks ${marks}`; // slice
  } else if (marks < 94 && marks > 80) {
    return `Grade: A with marks ${marks}`; // slice
  } else if (marks < 80 && marks > 70) {
    return `Grade: B with marks ${marks}`;
  } else if (marks < 70 && marks > 60) {
    return `Grade: C with marks ${marks}`;
  } else {
    return `Grade: F with marks ${marks}`;
  }
  return 'Something else';
}

function removeHtmlMarkupWithoutBraces(s) {
  let tag = false;
  let quote = false;
  let out = '';
  let a = 3;
  
  for (let c of s) {
    for (let i = 0; i < 5; i++) {
      if (c === '<' && !quote)
        tag = true;
      else if (c === '>' && !quote)
        tag = false;
      else if (c === '"' || c === "'" && tag)
        quote = !quote; // slice
      else if (!tag)
        out = out + c;
      else
        tag = out + quote;
    }
  }
  
  console.assert(out.includes('<') === -1);
  return out;
}

function getExamGradeWithThreshold2(marks, threshold) {
  marks = marks / threshold;
  if (marks > 95) {
    if (marks + threshold > 100) 
      return marks + ' 100';
  } else if (marks < 94 && marks > 80) {
    return `Grade: A with marks ${marks}`; // slice
  } else if (marks < 80 && marks > 70) {
    return `Grade: B with marks ${marks}`;
  } else if (marks < 70 && marks > 60) {
    return `Grade: C with marks ${marks}`;
  } else {
    return `Grade: F with marks ${marks}`;
  }
  return 'Something else';
}
