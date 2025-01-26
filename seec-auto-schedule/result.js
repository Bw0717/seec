// 當結果頁面載入時
document.addEventListener('DOMContentLoaded', function() {
    // 從 localStorage 獲取結果
    const results = JSON.parse(localStorage.getItem('scheduleResults'));
    if (!results) {
        alert('無法獲取排程結果！');
        return;
    }
    
    // 顯示結果
    displayResults(results);
});

// 顯示結果
function displayResults(results) {
    const resultDiv = document.getElementById('scheduleResult');
    
    // 按產線分組顯示結果
    const groupedAssignments = groupByLine(results.assignments);
    
    resultDiv.innerHTML = `
        <div class="result-timestamp">
            排程時間：${new Date(results.timestamp).toLocaleString()}
        </div>
        <div class="result-assignments">
            ${Object.entries(groupedAssignments).map(([lineName, assignments]) => `
                <div class="line-assignments">
                    <h3 class="line-name">${lineName}</h3>
                    <div class="assignments-container">
                        ${assignments.map(assignment => `
                            <div class="assignment-item">
                                <div class="assignment-header">
                                    <span class="person-name">${assignment.person.name}</span>
                                    <span class="station-order">順序: ${assignment.station.order || 0}</span>
                                </div>
                                <div class="assignment-details">
                                    <p>工作站：${assignment.station.name}</p>
                                    ${assignment.station.highPriority ? '<span class="badge">不受人數限制</span>' : ''}
                                    ${assignment.station.priorityAssign ? '<span class="badge">優先分配</span>' : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// 將分配結果按產線分組，並按工作站順序排序
function groupByLine(assignments) {
    // 先按產線分組
    const groups = assignments.reduce((groups, assignment) => {
        const lineName = assignment.line.name;
        if (!groups[lineName]) {
            groups[lineName] = [];
        }
        groups[lineName].push(assignment);
        return groups;
    }, {});

    // 對每個產線內的分配按工作站順序排序
    Object.keys(groups).forEach(lineName => {
        groups[lineName].sort((a, b) => {
            const orderA = a.station.order || 0;
            const orderB = b.station.order || 0;
            return orderA - orderB;
        });
    });

    return groups;
} 