// Copyright 2019 Workiva Inc.
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

export class Footnote {
    constructor(report, footnoteId, title) {
        this.id = footnoteId;
        this.linkedFacts = [];
        this.title = title;
        this.ixNode = report.getIXNodeForItemId(footnoteId);
    }

    // Facts that are the source of relationships to this fact.
    addLinkedFact(f) {
        this.linkedFacts.push(f); 
    }

    textContent() {
        return this.ixNode.textContent();
    }

    readableValue() {
        return this.textContent();
    }

    isTextBlock() {
        return false;
    }
}
