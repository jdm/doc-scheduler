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
    rebuildCalendar(currentDate, [], []);
    createSchedule();
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
    rebuildCalendar(currentDate, [], []);
    createSchedule();
}

function rebuildCalendar(date, shifts, docs) {
    //console.log(shifts, docs);
    const year = date.getFullYear();
    const month = date.getMonth();
    const startDate = new Date(year, month, 1);
    const startDay = startDate.getDay();
    document.querySelector("#year").textContent = startDate.getFullYear();
    document.querySelector("#month").textContent = startDate.toLocaleString('default', { month: 'long' });

    const days = document.querySelector("#days");
    days.innerHTML = "";

    const prevMonth = calcPrevMonth(currentDate).getMonth();
    for (i = 0; i < startDay; i++) {
        const day = document.createElement("li");
        day.innerText = daysInMonth(prevMonth, year) - startDay + i + 1;
        days.appendChild(day);
    }

    for (i = 0; i < daysInMonth(month, year); i++) {
        const day = document.createElement("li");
        const dayShifts = shifts.length > i ? shifts[i].map(id => id !== null ? docs[id] : null) : [null, null];
        const firstClass = dayShifts[0] ? "filled" : "unfilled";
        const secondClass = dayShifts[1] ? "filled" : "unfilled";
        const firstShift = dayShifts[0] || "&lt;unfilled&gt;";
        const secondShift = dayShifts[1] || "&lt;unfilled&gt;";
        day.innerHTML = `${i + 1}<br><span class="${firstClass}">${firstShift}</span><br><span class="${secondClass}">${secondShift}</span>`;
        days.appendChild(day);
    }
}

rebuildCalendar(currentDate, [], []);

const body = [
    {
        "name": "Bowman",
        "preferred": [
            1,
            8,
            15,
            22,
            30,
        ],
        "unavailable": [
            2,
            9,
            16,
            23
        ],
        "min": 0,
        "max": 4
    },
    {
        "name": "Curtis",
        "preferred": [
            3,
            4,
            10,
            11,
            17,
            18,
            24,
            25,
        ],
        "unavailable": [],
        "min": 4,
        "max": 6
    },
    {
        "name": "McArthur",
        "preferred": [
        ],
        "unavailable": [],
        "min": 0,
        "max": 8
    },
    {
        "name": "Hubbs",
        "preferred": [
        ],
        "unavailable": [],
        "min": 3,
        "max": 7
    },
    {
        "name": "AlQaseer",
        "preferred": [
        ],
        "unavailable": [],
        "min": 4,
        "max": 8
    },
    {
        "name": "Doan",
        "preferred": [
        ],
        "unavailable": [],
        "min": 2,
        "max": 5
    },
    {
        "name": "Gill",
        "preferred": [
        ],
        "unavailable": [],
        "min": 4,
        "max": 6,
    },
    {
        "name": "Scheuerman",
        "preferred": [],
        "unavailable": [],
        "min": 4,
        "max": 6,
    }
];
function createSchedule() {
    const days = daysInMonth(currentDate.getMonth(), currentDate.getYear());
    fetch(`cgi-bin/solve-cgi.py?days=${days}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    }).then(response => response.json())
        .then(data => rebuildCalendar(currentDate, data, body.map(doc => doc["name"])));
}

createSchedule();

