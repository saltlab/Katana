const { parseModuleWithLocation } = require('shift-parser');
const fs = require('fs');
const path = require('path');

const unslicedPath = process.argv[2];
const slicedPath = process.argv[3];
const isDual = process.argv[4] === 'dual' ? true : false;
console.log(`Unsliced path ${unslicedPath}`);
console.log(`Sliced path ${slicedPath}`);


function _getPrefix(filename) {
	if (filename.endsWith('_babel.js')) {
        return filename.includes('_buggy_babel.js') ? filename.split('_buggy_babel.js')[0] : filename.split('_fixed_babel.js')[0];
	}
    if (filename.endsWith('_buggy.js') || filename.endsWith('_fixed.js')) {
        return filename.includes('_buggy.js') ? filename.split('_buggy.js')[0] : filename.split('_fixed.js')[0];
	}
}

const invalidFileMap = [];
const fileMap = {};
fs.readdirSync(slicedPath).forEach(file => {
    if (file.endsWith('.js')) {
		const filePath = path.join(slicedPath, file);
		const text = fs.readFileSync(filePath, 'utf8');

		if (text.trim() === '') {
			console.log(`File ${file} contents are empty`);
		} else {
			const prefix = _getPrefix(file);
			try {
				const ast = parseModuleWithLocation(text);
				console.log('Processed AST of file ----', file);

				if (fileMap.hasOwnProperty(prefix)) {
					fileMap[prefix].push(file);
				} else {
					fileMap[prefix] = [file];
				}
			} catch(e) {
				console.log('FAILED to parse AST...', file);
				if (invalidFileMap.hasOwnProperty(prefix)) {
					invalidFileMap[prefix].push(file);
				} else {
					invalidFileMap[prefix] = [file];
				}
			}
		}
    }
});

console.log('Number of parsable datapoints', Object.keys(fileMap).length);

function getPrunedFilesWithoutPair(filemap) {
	const clonedFileMap = Object.assign({}, filemap);

	for (const [key, value] of Object.entries(filemap)) {
		if (value.length !== 2) {
			delete clonedFileMap[key];
		}	
	}
	return clonedFileMap;
}

const clonedFileMap = getPrunedFilesWithoutPair(fileMap);
const clonedInvalidFileMap = getPrunedFilesWithoutPair(invalidFileMap);

function createTempDir(dir) {
	if (!fs.existsSync(dir)){
		fs.mkdirSync(dir, { recursive: true });
	}
}

const newSlicedDir = unslicedPath + `/sliced_pruned${isDual ? '_dual' : ''}`;
const newUnslicedDir = unslicedPath + `/unsliced_pruned${isDual ? '_dual' : ''}`;
const newSlicedDirInvalid = unslicedPath + `/sliced_invalid${isDual ? '_dual' : ''}`;
const newUnslicedDirInvalid = unslicedPath + `/unsliced_invalid${isDual ? '_dual' : ''}`;

createTempDir(newSlicedDir);
createTempDir(newUnslicedDir);
createTempDir(newSlicedDirInvalid);
createTempDir(newUnslicedDirInvalid);


function renameFileWithBabelSuffix(filename, prefix) {
	if (filename.endsWith('_buggy.js')) {
		return prefix + '_buggy_babel.js';
	}
	return prefix + '_fixed_babel.js';
}

for (const [key, value] of Object.entries(clonedFileMap)) {
	for (const file of value) {
		fs.copyFileSync(slicedPath + '/' + file, newSlicedDir + '/' + file);
		fs.copyFileSync(unslicedPath + '/' + file, newUnslicedDir + '/' + file);
	}
}

for (const [key, value] of Object.entries(clonedInvalidFileMap)) {
	for (const file of value) {
		fs.copyFileSync(slicedPath + '/' + file, newSlicedDirInvalid + '/' + file);
		fs.copyFileSync(unslicedPath + '/' + file, newUnslicedDirInvalid + '/' + file);
	}
}
