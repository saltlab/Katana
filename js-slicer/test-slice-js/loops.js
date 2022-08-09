function removeHtmlMarkup(s) {
  let tag = false;
  let quote = false;
  let out = '';
  let a = 3;
  
  for (let c of s) {
    for (let i = 0; i < 5; i++) {
      if (c === '<' && !quote) {
        tag = true; // slice
      } else if (c === '>' && !quote) {
        tag = false;
      } else if (c === '"' || c === "'" && tag) {
        quote = !quote;
      } else if (!tag) {
        out = out + c;
      }
    }
  }
  
  console.assert(out.includes('<') === -1);
  return out;
}


let n = 0;
let product = 1;
let sum = 1;
let x = window.prompt("Input");
while (x >= 0){
  sum = sum + x;
  product = product * x ;
  n = n + 1;
  x = window.prompt("Input");
}
average = (sum - 1) / n;
console.log("The total is",sum); // slice
console.log("The product is",product);
console.log("The average is",average);
