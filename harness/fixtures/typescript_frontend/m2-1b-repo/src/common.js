require("setup");
const client = require("./client");
module.exports = client;
exports.client = client;

function unsupportedNested() {
  require("nested");
}

require("node:fs").writeFileSync("executed.txt", "must-not-run");
