const Git = require("nodegit");
const fs = require("fs");
const csv = require("csv-parser");
const results = [];

function getRepositories() {
  const baseURL = "https://github.com/";
  fs.createReadStream("repos.csv")
    .pipe(csv())
    .on("data", (data) => results.push(data))
    .on("end", () => {
      let count = 1;
      results.forEach((repo) => {
        console.log(
          `Cloning ${count} repository`,
          repo.Username,
          "/",
          repo.Project
        );
        Git.Clone(
          `${baseURL}${repo.Username}/${repo.Project}`,
          `./repositories/${repo.Project}`
        );
        count += 1;
      });
    });
}
getRepositories();

