const fs = require("fs")
const parse = require("shift-parser").parseModule;

if (process.argv.length < 4){
	console.log("please specify src file and AST output file")
	process.exit(1)
}

const src_file = process.argv[2]
const ast_file = process.argv[3]

src = fs.readFileSync(src_file, "utf-8")
ast = parse(src)

fs.writeFile(ast_file, JSON.stringify(ast, null, 4), function(err){
	if (err) {
		console.log(err);
		return;
	}
});

