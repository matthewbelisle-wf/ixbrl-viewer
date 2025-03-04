// Copyright 2023 Workiva Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const exec = require('child_process');

function git_describe() {
    if (process.env.GIT_TAG !== undefined) {
        return process.env.GIT_TAG;
    }
    return exec.execSync("git describe --tags --dirty", {encoding: "utf-8"}).trim();
}

module.exports = {
    dev_version: function() {
        return git_describe() + "-dev";
    },
    prod_version: function() {
        return git_describe();
    }
};
