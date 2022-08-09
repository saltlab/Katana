const fs = require("fs")
const jsonpatch = require('fast-json-patch')

if (process.argv.length < 5){
	console.log("please specify buggy file, fixed file, and AST file")
	process.exit(1)
}

var buggyFile = process.argv[2]
var fixedFile = process.argv[3]
var astFile = process.argv[4]

s_buggy = fs.readFileSync(buggyFile, "utf-8")
s_fixed = fs.readFileSync(fixedFile, "utf-8")

obj_buggy = JSON.parse(s_buggy)
obj_fixed = JSON.parse(s_fixed)

diff = jsonpatch.compare(obj_buggy, obj_fixed)


if (diff.length === 1) {
	let prefix = astFile.split('_ast_diff.txt')[0].split('/');
	prefix = prefix[prefix.length - 1];
	console.log('One diff file -- ', prefix);
	fs.writeFile(astFile, JSON.stringify(diff, null, 4), function(err){
		if (err) {
			console.log(err);
			return;
		}
	});	
}
