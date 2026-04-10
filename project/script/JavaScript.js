const alliancesData = {
    'Пупкина': [
        { name: 'Группа Сизых', employees: ['Сизый Александр Петрович', 'Сизый Мария Ивановна'] },
        { name: 'Группа Василькова', employees: ['Васильков Иван Сергеевич', 'Василькова Ольга Васильевна'] },
        { name: 'Группа Петькова', employees: ['Петьков Дмитрий Алексеевич', 'Петькова Елена Дмитриевна'] },
        { name: 'Группа Ивановых', employees: ['Ивановых Николай Петрович', 'Ивановых Анна Николаевна'] }
    ],
    'Тумбочкина': [
        { name: 'Группа Кузнецовых', employees: ['Кузнецов Виктор Михайлович', 'Кузнецова Светлана Викторовна'] },
        { name: 'Группа Смирновых', employees: ['Смирновых Алексей Иванович', 'Смирновых Наталья Алексеевна'] },
        { name: 'Группа Поповых', employees: ['Поповых Евгений Сергеевич', 'Поповых Ирина Евгеньевна'] },
        { name: 'Группа Волковых', employees: ['Волковых Павел Дмитриевич', 'Волкова Екатерина Павловна'] }
    ],
    'Петровича': [
        { name: 'Группа Морозовых', employees: ['Морозовых Андрей Владимирович', 'Морозова Ольга Андреевна'] },
        { name: 'Группа Лебедевых', employees: ['Лебедевых Сергей Николаевич', 'Лебедева Мария Сергеевна'] },
        { name: 'Группа Козловых', employees: ['Козловых Дмитрий Юрьевич', 'Козлова Анна Дмитриевна'] },
        { name: 'Группа Соболевых', employees: ['Соболевых Иван Петрович', 'Соболева Елена Ивановна'] }
    ],
    'Сидоровича': [
        { name: 'Группа Никифоровых', employees: ['Никифоровых Роман Александрович', 'Никифорова Татьяна Романовна'] },
        { name: 'Группа Поляковых', employees: ['Поляковых Михаил Васильевич', 'Полякова Ирина Михайловна'] },
        { name: 'Группа Савельевых', employees: ['Савельевых Алексей Константинович', 'Савельева Надежда Алексеевна'] },
        { name: 'Группа Тарасовых', employees: ['Тарасовых Владимир Сергеевич', 'Тарасова Ольга Владимировна'] }
    ]
};

let currentDeleteCallback = null;

document.addEventListener('DOMContentLoaded', () => {
    generateDateOptions();
    generateTimeOptions('startTime');
    generateTimeOptions('endTime');
    const employees = JSON.parse(localStorage.getItem('employees') || '[]');
    updateTable(employees);
    calculateSummary(employees);
});

function updateGroups() {
    const alliance = document.getElementById('alliance').value;
    const groupSelect = document.getElementById('group');
    const employeeSelect = document.getElementById('employee');
    const scheduleForm = document.getElementById('scheduleForm');
    groupSelect.innerHTML = '<option value="">-- Выберите группу --</option>';
    employeeSelect.innerHTML = '<option value="">-- Сначала выберите группу --</option>';
    employeeSelect.disabled = true;
    if (alliance && alliancesData[alliance]) {
        alliancesData[alliance].forEach(group => {
            const option = document.createElement('option');
            option.value = group.name;
            option.textContent = group.name;
            groupSelect.appendChild(option);
        });
        groupSelect.disabled = false;
        scheduleForm.style.display = 'block';
    } else {
        groupSelect.disabled = true;
        scheduleForm.style.display = 'none';
    }
}

function updateEmployees() {
    const alliance = document.getElementById('alliance').value;
    const group = document.getElementById('group').value;
    const employeeSelect = document.getElementById('employee');
    employeeSelect.innerHTML = '<option value="">-- Выберите сотрудника --</option>';
    if (alliance && group) {
        const selectedGroup = alliancesData[alliance].find(g => g.name === group);
        if (selectedGroup) {
            selectedGroup.employees.forEach(emp => {
                const option = document.createElement('option');
                option.value = emp;
                option.textContent = emp;
                employeeSelect.appendChild(option);
            });
            employeeSelect.disabled = false;
        }
    }
}

function generateDateOptions() {
    const dateSelect = document.getElementById('date');
    const today = new Date();
    for (let i = 0; i < 30; i++) {
        const date = new Date(today);
        date.setDate(today.getDate() + i);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const formattedDate = `${year}-${month}-${day}`;
        const weekdays = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
        const weekday = weekdays[date.getDay()];
        const option = document.createElement('option');
        option.value = formattedDate;
        option.textContent = `${formattedDate} (${weekday})`;
        dateSelect.appendChild(option);
    }
}

function generateTimeOptions(selectId) {
    const select = document.getElementById(selectId);
    select.innerHTML = '<option value="">-- Выберите время --</option>';
    if (selectId === 'startTime') {
        const dayOff = document.createElement('option');
        dayOff.value = 'Выходной';
        dayOff.textContent = '🚫 Выходной';
        select.appendChild(dayOff);
    }
    for (let hour = 0; hour < 24; hour++) {
        for (let minute of [0, 15, 30, 45]) {
            if (selectId === 'startTime' && (hour < 6 || (hour === 6 && minute < 30))) continue;
            const timeValue = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
            const option = document.createElement('option');
            option.value = timeValue;
            option.textContent = timeValue;
            select.appendChild(option);
        }
    }
}

function toggleEndTime() {
    const startTime = document.getElementById('startTime').value;
    const endTimeSelect = document.getElementById('endTime');
    if (startTime === 'Выходной') {
        endTimeSelect.disabled = true;
        endTimeSelect.value = '';
        endTimeSelect.innerHTML = '<option value="">-- Выберите время --</option>';
    } else if (startTime) {
        endTimeSelect.disabled = false;
        endTimeSelect.innerHTML = '<option value="">-- Выберите время --</option>';
        const [startHour, startMinute] = startTime.split(':').map(Number);
        const startTotal = startHour * 60 + startMinute;
        for (let hour = 0; hour < 25; hour++) {
            for (let minute of [0, 15, 30, 45]) {
                if (hour === 24 && minute > 0) continue;
                let endHour = hour, displayHour = hour, nextDay = false;
                if (hour === 24) { displayHour = 0; nextDay = true; }
                let endTotal = (hour === 24 ? 1440 : hour * 60 + minute);
                let adjustedEnd = endTotal;
                if (hour < 6 && hour !== 24) adjustedEnd += 1440;
                if (adjustedEnd <= startTotal) continue;
                if (adjustedEnd - startTotal > 720) continue;
                if (hour > 2 && hour < 6 && hour !== 24) continue;
                const timeValue = `${String(endHour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
                const label = nextDay ? `${String(displayHour).padStart(2, '0')}:${String(minute).padStart(2, '0')} (след. день)` : `${String(displayHour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
                const opt = document.createElement('option');
                opt.value = timeValue;
                opt.textContent = label;
                endTimeSelect.appendChild(opt);
            }
        }
    }
}

function checkConsecutiveShifts(employee, newDate) {
    if (!employee) return { canAdd: true, count: 0 };
    const sorted = [...employee.shifts].sort((a,b)=>new Date(a.date)-new Date(b.date));
    let allDates = [...sorted.map(s=>s.date), newDate].sort();
    let maxConsec=1, cur=1;
    for(let i=1;i<allDates.length;i++){
        const diff = (new Date(allDates[i]) - new Date(allDates[i-1])) / (86400000);
        if(diff===1) cur++; else cur=1;
        maxConsec=Math.max(maxConsec,cur);
    }
    return { canAdd: maxConsec <= 6, count: maxConsec };
}

function calculateMaxConsecutiveShifts(employee) {
    if(!employee?.shifts.length) return 0;
    const sorted = [...employee.shifts].sort((a,b)=>new Date(a.date)-new Date(b.date));
    let max=1, cur=1;
    for(let i=1;i<sorted.length;i++){
        const diff = (new Date(sorted[i].date) - new Date(sorted[i-1].date))/86400000;
        if(diff===1) cur++; else cur=1;
        max=Math.max(max,cur);
    }
    return max;
}

function calculateEmployeeMetrics(emp){
    let weekday=0, weekend=0;
    emp.shifts.forEach(s=>{
        const day=new Date(s.date).getDay();
        if(day>=1 && day<=5) weekday++; else weekend++;
    });
    const total=emp.shifts.length||1;
    return { weekdayPercentage: ((weekday/total)*100).toFixed(2), weekendPercentage: ((weekend/total)*100).toFixed(2) };
}

function calculateSummary(employees){
    let totalShifts=0, shiftsByDay=[0,0,0,0,0,0,0], before11=0, after19=0, longShifts=0, excessConsecutive=0;
    const dayNames=['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье'];
    employees.forEach(emp=>{
        if(calculateMaxConsecutiveShifts(emp)>6) excessConsecutive++;
        emp.shifts.forEach(shift=>{
            totalShifts++;
            const date=new Date(shift.date);
            let dayIdx=date.getDay(); if(dayIdx===0) dayIdx=6; else dayIdx--;
            shiftsByDay[dayIdx]++;
            if(shift.startTime!=='Выходной'){
                const startH=parseInt(shift.startTime.split(':')[0]);
                if(startH<11) before11++;
                if(shift.endTime){
                    let [sh,sm]=shift.startTime.split(':').map(Number);
                    let [eh,em]=shift.endTime.split(':').map(Number);
                    let startM=sh*60+sm, endM=eh*60+em;
                    if(eh<6 && eh!==0) endM+=1440;
                    if(eh===0 && em===0 && sh>0) endM+=1440;
                    if(endM-startM>720) longShifts++;
                    let endH=eh;
                    if(shift.endTime==='00:00' && sh<19) after19++;
                    else if(endH>19) after19++;
                }
            }
        });
    });
    if(totalShifts){
        let html='<div class="stat-card"><div class="stat-title"><i class="fas fa-chart-line"></i> Распределение по дням</div><div class="weekday-stats">';
        for(let i=0;i<7;i++){
            let perc=((shiftsByDay[i]/totalShifts)*100).toFixed(2);
            html+=`<div class="day-row"><span class="day-name">${dayNames[i]}</span><div class="day-bar-container"><div class="day-bar" style="width:${Math.min(perc,100)}%"></div></div><span class="day-percent">${perc}%</span></div>`;
        }
        html+=`</div></div><div class="stat-card"><div class="stat-title"><i class="fas fa-sun"></i> Временные метрики</div>
        <div class="day-row"><span>До 11:00</span><span><strong>${((before11/totalShifts)*100).toFixed(2)}%</strong> (${before11})</span></div>
        <div class="day-row"><span>После 19:00</span><span><strong>${((after19/totalShifts)*100).toFixed(2)}%</strong> (${after19})</span></div>
        </div>`;
        document.getElementById('summaryWeekdays').innerHTML = html;
        let warnings=[];
        if(excessConsecutive) warnings.push(`⚠️ ${excessConsecutive} сотрудник(ов) имеют >6 смен подряд`);
        if(longShifts) warnings.push(`⚠️ ${longShifts} смен(ы) длительностью более 12ч`);
        document.getElementById('summaryWeekends').innerHTML = warnings.length ? `<i class="fas fa-exclamation-triangle"></i> ${warnings.join('<br>')}` : '<i class="fas fa-check-circle"></i> Нарушений не обнаружено';
    } else {
        document.getElementById('summaryWeekdays').innerHTML = '<div class="stat-card">Нет данных</div>';
        document.getElementById('summaryWeekends').innerHTML = '';
    }
}

function updateTable(employees) {
    const container=document.getElementById('employeesTable');
    container.innerHTML='';
    if(employees.length===0){ container.innerHTML='<div style="background:white; border-radius:28px; padding:32px; text-align:center">📭 Нет внесенных графиков</div>'; return; }
    const grouped={};
    employees.forEach((emp,idx)=>{ if(!grouped[emp.alliance]) grouped[emp.alliance]={}; if(!grouped[emp.alliance][emp.group]) grouped[emp.alliance][emp.group]=[]; grouped[emp.alliance][emp.group].push({...emp,index:idx}); });
    for(const alliance in grouped){
        const tableDiv=document.createElement('div'); tableDiv.className='alliance-table';
        const caption=document.createElement('caption'); caption.innerHTML=`<i class="fas fa-building"></i> ${alliance}`;
        const tbl=document.createElement('table');
        tbl.innerHTML=`<thead><tr><th>Группа</th><th>Сотрудник</th><th>Смены</th><th>Макс. подряд</th><th>% будни</th><th>% выходные</th><th>Действия</th></tr></thead><tbody></tbody>`;
        const tbody=tbl.querySelector('tbody');
        for(const group in grouped[alliance]){
            grouped[alliance][group].forEach(emp=>{
                const metrics=calculateEmployeeMetrics(emp);
                const maxSeq=calculateMaxConsecutiveShifts(emp);
                const shiftsText=emp.shifts.map(s=>`${s.date} (${s.startTime}${s.endTime?`-${s.endTime}`:''})`).join('; ');
                const row=tbody.insertRow();
                row.insertCell(0).innerHTML=group;
                row.insertCell(1).innerHTML=emp.name;
                row.insertCell(2).innerHTML=shiftsText.substring(0,70)+(shiftsText.length>70?'...':'');
                row.insertCell(3).innerHTML=`<span class="${maxSeq>6?'warning':''}">${maxSeq}</span>`;
                row.insertCell(4).innerHTML=metrics.weekdayPercentage+'%';
                row.insertCell(5).innerHTML=metrics.weekendPercentage+'%';
                const actions=row.insertCell(6);
                actions.className='action-buttons';
                actions.innerHTML=`<button class="edit-btn" onclick="window.showEmployeeDetails(${emp.index})"><i class="fas fa-edit"></i></button>
                                <button class="delete-btn" onclick="window.prepareDeleteEmployee(${emp.index}, '${emp.name.replace(/'/g,"\\'")}')"><i class="fas fa-trash"></i></button>`;
            });
        }
        tableDiv.appendChild(caption); tableDiv.appendChild(tbl); container.appendChild(tableDiv);
    }
}

window.showEmployeeDetails = function(idx){
    const employees=JSON.parse(localStorage.getItem('employees')||'[]');
    const emp=employees[idx];
    if(!emp) return;
    document.getElementById('employeeDetails').style.display='block';
    document.getElementById('detailsEmployeeName').innerHTML=`<i class="fas fa-user-circle"></i> ${emp.name}`;
    document.getElementById('detailsAllianceGroup').innerHTML=`${emp.alliance} · ${emp.group}`;
    const listDiv=document.getElementById('shiftsList');
    listDiv.innerHTML='';
    [...emp.shifts].sort((a,b)=>new Date(a.date)-new Date(b.date)).forEach((shift, sidx)=>{
        const div=document.createElement('div'); div.className='shift-item';
        const dateObj=new Date(shift.date); const weekdays=['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
        const dayLabel=weekdays[dateObj.getDay()];
        const info=`${shift.date} (${dayLabel}) — ${shift.startTime==='Выходной'?'Выходной':`${shift.startTime} - ${shift.endTime||''}`}`;
        div.innerHTML=`<span><i class="far fa-calendar-alt"></i> ${info}</span><button class="delete-shift-btn" onclick="window.prepareDeleteShift(${idx}, ${sidx})"><i class="fas fa-times"></i> Удалить</button>`;
        listDiv.appendChild(div);
    });
    const delEmpBtn=document.createElement('button'); delEmpBtn.className='delete-btn'; delEmpBtn.style.marginTop='16px';
    delEmpBtn.innerHTML='<i class="fas fa-user-slash"></i> Удалить сотрудника полностью';
    delEmpBtn.onclick=()=>prepareDeleteEmployee(idx, emp.name);
    listDiv.appendChild(delEmpBtn);
};

window.prepareDeleteShift=(empIdx,shiftIdx)=>showDeleteModal('Удалить эту смену?',()=>deleteShift(empIdx,shiftIdx));
window.prepareDeleteEmployee=(empIdx,name)=>showDeleteModal(`Удалить сотрудника ${name} и все смены?`,()=>deleteEmployee(empIdx));

function deleteShift(empIdx,shiftIdx){
    let employees=JSON.parse(localStorage.getItem('employees')||'[]');
    if(employees[empIdx]?.shifts[shiftIdx]) employees[empIdx].shifts.splice(shiftIdx,1);
    if(employees[empIdx]?.shifts.length===0) employees.splice(empIdx,1);
    localStorage.setItem('employees',JSON.stringify(employees));
    updateTable(employees); calculateSummary(employees);
    document.getElementById('employeeDetails').style.display='none';
}

function deleteEmployee(empIdx){
    let employees=JSON.parse(localStorage.getItem('employees')||'[]');
    employees.splice(empIdx,1);
    localStorage.setItem('employees',JSON.stringify(employees));
    updateTable(employees); calculateSummary(employees);
    document.getElementById('employeeDetails').style.display='none';
}

function hideEmployeeDetails(){ document.getElementById('employeeDetails').style.display='none'; }

function showDeleteModal(msg,cb){ document.getElementById('deleteModalMessage').innerHTML=msg; currentDeleteCallback=cb; document.getElementById('deleteModal').style.display='flex'; }
function closeDeleteModal(){ document.getElementById('deleteModal').style.display='none'; currentDeleteCallback=null; }

document.getElementById('confirmDeleteBtn').onclick=()=>{ if(currentDeleteCallback) currentDeleteCallback(); closeDeleteModal(); };
window.onclick=e=>{ if(e.target===document.getElementById('deleteModal')) closeDeleteModal(); };

function updateConsecutiveWarning(){
    const alliance=document.getElementById('alliance').value, group=document.getElementById('group').value, name=document.getElementById('employee').value, date=document.getElementById('date').value;
    if(alliance&&group&&name&&date){
        const employees=JSON.parse(localStorage.getItem('employees')||'[]');
        const emp=employees.find(e=>e.name===name&&e.alliance===alliance&&e.group===group);
        if(emp){
            const check=checkConsecutiveShifts(emp,date);
            const warnDiv=document.getElementById('consecutiveWarning');
            if(!check.canAdd){ warnDiv.style.display='block'; warnDiv.innerHTML=`⚠️ Ошибка: будет ${check.count} смен подряд (макс 6)!`; warnDiv.style.background='#ffe6e6'; }
            else if(check.count>4){ warnDiv.style.display='block'; warnDiv.innerHTML=`⚠️ Внимание: ${check.count} смен подряд. Осталось ${6-check.count} до лимита.`; warnDiv.style.background='#fff3e0'; }
            else warnDiv.style.display='none';
        }
    }
}

document.getElementById('employee')?.addEventListener('change',updateConsecutiveWarning);
document.getElementById('date')?.addEventListener('change',updateConsecutiveWarning);

document.getElementById('scheduleForm').addEventListener('submit',function(e){
    e.preventDefault();
    const alliance=document.getElementById('alliance').value, group=document.getElementById('group').value, name=document.getElementById('employee').value, date=document.getElementById('date').value, start=document.getElementById('startTime').value, end=document.getElementById('endTime').value;
    if(!alliance||!group||!name||!date||!start) return showError('Заполните все поля');
    if(start!=='Выходной' && !end) return showError('Укажите конец смены');
    let employees=JSON.parse(localStorage.getItem('employees')||'[]');
    let existing=employees.find(e=>e.name===name&&e.alliance===alliance&&e.group===group);
    if(existing && !checkConsecutiveShifts(existing,date).canAdd) return showError('❌ Превышение 6 смен подряд');
    const shift={date,startTime:start,endTime:start==='Выходной'?'':end};
    if(existing) existing.shifts.push(shift);
    else employees.push({name,alliance,group,shifts:[shift]});
    localStorage.setItem('employees',JSON.stringify(employees));
    updateTable(employees); calculateSummary(employees);
    document.getElementById('startTime').value=''; document.getElementById('endTime').innerHTML='<option value="">-- Выберите время --</option>'; document.getElementById('endTime').disabled=true;
    document.getElementById('consecutiveWarning').style.display='none';
    showError('');
});

function showError(msg){ const errDiv=document.getElementById('errorMessage'); if(errDiv) errDiv.innerHTML=msg; else console.log(msg); }
window.showError=showError;