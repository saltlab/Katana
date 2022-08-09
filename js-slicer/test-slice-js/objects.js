let obj = [
  {
      fruit: 'apple',
      color: 'red',
      variant: ['red', 'green'] // slice
  }
];

module.exports = {
  obj // slice
};

const label = 'Color';

const newObj = obj
  .forEach(o => console.log(o))
  .map(o => label + ' ' + o.color) // slice
  .filter(o => o.variant.includes('red'))
  .sort();
