function daysInMonth(month, year) {
    const isLeap = year => new Date(year, 1, 29).getDate() === 29;
    if (month == 1 && isLeap(year)) {
        return 29;
    }
    const days = [
        31,
        28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ];
    return days[month];
}
let currentDate = new Date();

function calcPrevMonth(date) {
    let year = date.getFullYear();
    let month = date.getMonth();
    if (month > 0) {
        month -= 1;
    } else {
        month = 11;
        year -= 1;
    }
    return new Date(year, month, 1);
}

function prevMonth() {
    currentDate = calcPrevMonth(currentDate);
    resetState();
    rebuildDocs();
    doRebuild();
}

function nextMonth() {
    let year = currentDate.getFullYear();
    let month = currentDate.getMonth();
    if (month < 11) {
        month += 1;
    } else {
        month = 0;
        year += 1;
    }
    currentDate = new Date(year, month, 1);
    resetState();
    rebuildDocs();
    doRebuild();
}

function rebuildCalendar(date, shifts, docs, active) {
    console.log(shifts, docs);
    const year = date.getFullYear();
    const month = date.getMonth();
    const startDate = new Date(year, month, 1);
    const startDay = startDate.getDay();
    document.querySelector("#year").textContent = startDate.getFullYear();
    document.querySelector("#month").textContent = startDate.toLocaleString('default', { month: 'long' });

    const days = document.querySelector("#days");
    days.innerHTML = "";

    const prevMonth = calcPrevMonth(currentDate).getMonth();
    for (let i = 0; i < startDay; i++) {
        const day = document.createElement("div");
        day.className = "disabled";
        day.innerHTML = `${daysInMonth(prevMonth, year) - startDay + i + 1}<br>&nbsp;<br>&nbsp;<br>`;
        days.appendChild(day);
    }

    for (let i = 0; i < daysInMonth(month, year); i++) {
        const day = document.createElement("div");
        day.classList.add("day");
        const currentDay = i;
        if (active !== null) {
            if (calendarState === INPUT_CONSTRAINTS) {
                day.onclick = () => markDay(currentDay);
                if (active["preferred"].indexOf(currentDay) !== -1) {
                    day.classList.add("preferred");
                }
                if (active["unavailable"].indexOf(currentDay) !== -1) {
                    day.classList.add("unavailable");
                }
            } else if (shifts.length) {
                const activeId = docs.indexOf(active["name"]);
                if (shifts[i].indexOf(activeId) !== -1) {
                    day.classList.add("highlight");
                }
            }
        }
        const dayShifts = shifts !== null && shifts.length > i ? shifts[i].map(id => id !== null ? docs[id] : null) : ["&nbsp;", "&nbsp;"];
        const firstClass = dayShifts[0] !== null ? "filled" : "unfilled";
        const secondClass = dayShifts[1] !== null ? "filled" : "unfilled";
        const firstShift = dayShifts[0] !== null ? dayShifts[0] : "&lt;unfilled&gt;";
        const secondShift = dayShifts[1] !== null ? dayShifts[1] : "&lt;unfilled&gt;";
        day.innerHTML = `<span>${i + 1}</span><br><span class="${firstClass}">${firstShift}</span><br><span class="${secondClass}">${secondShift}</span>`;
        days.appendChild(day);
    }
}

let docs = {
    "2024-0": [
        {
            "name": "Bowman",
            "preferred": [
                1,5,7,9
            ],
            "unavailable": [13],
            "min": 1,
            "max": 8,
            "prefer_double": false,
        },
        {
            "name": "McArthur",
            "preferred": [11,20],
            "unavailable": [23],
            "min": 4,
            "max": 8,
            "prefer_double": false,
        },
        {
            "name": "AlQaseer",
            "preferred": [30],
            "unavailable": [8],
            "min": 2,
            "max": 8,
            "prefer_double": false,
        },
        {
            "name": "Ponessi",
            "preferred": [],
            "unavailable": [],
            "min": 4,
            "max": 8,
            "prefer_double": true,
        },
        {
            "name": "Hubbs",
            "preferred": [],
            "unavailable": [],
            "min": 4,
            "max": 8,
            "prefer_double": true,
        },
        {
            "name": "Kyle",
            "preferred": [],
            "unavailable": [],
            "min": 4,
            "max": 8,
            "prefer_double": false,
        },
        {
            "name": "Curtis",
            "preferred": [],
            "unavailable": [],
            "min": 4,
            "max": 8,
            "prefer_double": false,
        }
    ]
};
let currentDoc = null;

function docIndex(date) {
    const currentYear = date.getFullYear();
    const currentMonth = date.getMonth();
    return `${currentYear}-${currentMonth}`;
}

function currentDocs() {
    const idx = docIndex(currentDate);
    if (!(idx in docs)) {
        docs[idx] = [];
    }
    return docs[idx];
}

function addDoc() {
    const input = document.querySelector("#docName");
    
    currentDocs().push({
        "name": input.value,
        "unavailable": [],
        "preferred": [],
        "min": 4,
        "max": 8,
        "prefer_double": false,
    });
    input.value = "";
    rebuildDocs();
}

function clone() {
    const prevDate = calcPrevMonth(currentDate);
    const prevDocs = docs[docIndex(prevDate)];
    console.log(prevDocs);
    docs[docIndex(currentDate)] = prevDocs.map(doc => {
        const copy = JSON.parse(JSON.stringify(doc));
        copy.unavailable = [];
        copy.preferred = [];
        return copy;
    });
    console.log(currentDocs());
    rebuildDocs();
}

function rebuildDocs() {
    const cloneButton = document.querySelector("#clone");
    if (currentDocs().length) {
        cloneButton.classList.add("hidden");
    } else {
        cloneButton.classList.remove("hidden");
    }

    const names = document.querySelector("#docNames");
    names.innerHTML = "";
    for (const doc of currentDocs()) {
        const docElem = document.createElement("div");
        docElem.className = "doc";
        docElem.onclick = markActiveDoc;
        const removeElem = document.createElement("button");
        removeElem.textContent = "✗";
        removeElem.onclick = (ev) => {
            ev.stopPropagation();
            if (confirm("Are you sure you want to remove this doctor from the schedule?")) {
                const idx = currentDocs().indexOf(doc);
                currentDocs().splice(idx, 1);
                rebuildDocs();
            }
        };
        docElem.appendChild(removeElem);
        const nameElem = document.createElement("span");
        nameElem.textContent = doc["name"];
        docElem.appendChild(nameElem);
        const minElem = document.createElement("input");
        minElem.type = "number";
        minElem.value = doc["min"];
        minElem.size = 3;
        minElem.onchange = (ev) => updateMinMax("min", ev);
        const maxElem = document.createElement("input");
        maxElem.type = "number";
        maxElem.value = doc["max"];
        maxElem.size = 3;
        maxElem.onchange = (ev) => updateMinMax("max", ev);
        docElem.appendChild(minElem);
        docElem.appendChild(maxElem);
        const checkElem = document.createElement("input");
        checkElem.type = "checkbox";
        checkElem.checked = doc["prefer_double"];
        checkElem.onchange = (ev) => {
            const idx = currentDocs().indexOf(doc);
            currentDocs()[idx]["prefer_double"] = ev.target.checked;
            rebuildDocs();
        }
        docElem.appendChild(checkElem);
        names.appendChild(docElem);
    }
}

function updateMinMax(prop, event) {
    //event.stopPropagation();
    //event.preventDefault();
    const docList = document.querySelector("#docNames");
    const parent = event.target.parentNode;
    let doc = docList.querySelector("div");
    let i = 0;
    while (doc) {
        if (doc === parent) {
            break;
        }
        i++;
        doc = doc.nextElementSibling;
    }
    currentDocs()[i][prop] = parseInt(event.target.value);
    rebuildDocs();
}

function markActiveDoc(ev) {
    const target = ev === null ? null : ev.target.classList.contains("doc") ? ev.target : ev.target.parentNode;
    if (ev !== null && ev.target.nodeName == "INPUT") {
        return;
    }
    const names = document.querySelector("#docNames");
    let i = 0;
    let doc = names.querySelector("div");
    const lastCurrent = currentDoc;
    currentDoc = null;
    while (doc) {
        if (doc === target && lastCurrent != i) {
            currentDoc = i;
            doc.classList.add("active");
        } else {
            doc.classList.remove("active");
        }
        i++;
        doc = doc.nextSibling;
    }
    doRebuild();
}

function markDay(day) {
    if (currentDoc == null || calendarState != INPUT_CONSTRAINTS) {
        return;
    }
    const doc = currentDocs()[currentDoc];
    if (doc["preferred"].indexOf(day) !== -1) {
        doc["preferred"] = doc["preferred"].filter(d => d != day);
        doc["unavailable"].push(day);
    } else if (doc["unavailable"].indexOf(day) !== -1) {
        doc["unavailable"] = doc["unavailable"].filter(d => d != day);
    } else {
        doc["preferred"].push(day);
    }
    doRebuild();
}

const INPUT_CONSTRAINTS = 0;
const SHOW_SCHEDULE = 1;
let calendarState;
let schedule;

function resetState() {
    currentDoc = null;
    calendarState = INPUT_CONSTRAINTS;
    schedule = null;
}

function doRebuild() {
    rebuildCalendar(
        currentDate,
        schedule,
        currentDocs().map(doc => doc["name"]),
        currentDoc !== null ? currentDocs()[currentDoc] : null,
    );
}

resetState();
doRebuild();
rebuildDocs();

function validate(shifts, docs) {
    for (const docIdx in docs) {
        const doc = docs[docIdx];
        let numShifts = 0;
        let numPreferred = 0;
        let numUnavailable = 0;
        for (const i in shifts) {
            const shift = shifts[i];
            if (shift.indexOf(parseInt(docIdx)) !== -1) {
                numShifts += 1;
                if (doc["preferred"].indexOf(i) !== -1) {
                    numPreferred += 1;
                }
                if (doc["unavailable"].indexOf(i) !== -1) {
                    numUnavailable += 1;
                }
            }
        }
        if (numShifts < doc["min"]) {
            console.log(`${doc["name"]} did not meet minimum shifts (${numShifts} vs. ${doc["min"]}).`);
        }
        if (numShifts > doc["max"]) {
            console.log(`${doc["name"]} exceeded maximum shifts (${numShifts} vs. ${doc["max"]}).`);
        }
        if (numUnavailable > 0) {
            console.log(`${doc["name"]} had ${numUnavailable} shifts scheduled on unavailable days.`);
        }
    }
}

function exportSchedule() {
}

function createSchedule() {
    markActiveDoc(null);

    const spinner = document.querySelector("#spinner");
    spinner.classList.remove("hidden");

    const days = daysInMonth(currentDate.getMonth(), currentDate.getYear());
    fetch(`cgi-bin/solve-cgi.py?days=${days}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(currentDocs()),
    }).then(response => response.json())
        .then(data => {
            calendarState = SHOW_SCHEDULE;
            schedule = data;
            rebuildCalendar(currentDate, data, currentDocs().map(doc => doc["name"]), null);
            spinner.classList.add("hidden");
            if (!data.length) {
                document.querySelector("#export").disabled = true;
                alert("No schedule possible—too many unfilled shifts.");
            } else {
                validate(schedule, currentDocs());
                document.querySelector("#export").disabled = false;
            }
        })
}

