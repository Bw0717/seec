from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from pulp import LpMaximize, LpProblem, LpVariable, lpSum
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
# 設置允許的前端域名
CORS(app, origins=['https://your-frontend-domain.com'])
Talisman(app, content_security_policy=None)

# 添加速率限制
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/schedule', methods=['POST'])
def schedule():
    try:
        # 獲取前端傳來的數據
        data = request.json
        
        # 執行排程算法
        result = calculate_schedule(data)
        
        # 返回結果
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_schedule(data):
    # 從前端數據獲取人員和工作站
    personnel = data['personnel']
    stations_data = data['stations']
    
    # 設置 employees (保留 overpeople，排除休假人員)
    employees = [p['id'] for p in personnel if not p.get('onLeave', False)] + ["overpeople"]
    
    # 設置 stations
    stations = [s['id'] for s in stations_data]
    
    # 設置 capabilities
    capabilities = {}
    # 先設置 overpeople 的能力
    for s in stations:
        capabilities[("overpeople", s)] = 1  # overpeople 可以做任何工作站
    
    # 設置其他人員的能力
    for p in personnel:
        for s in stations:
            ability = 0
            if s in p['stationSettings']:
                ability = 1 if p['stationSettings'][s]['ability'] else 0
            capabilities[(p['id'], s)] = ability
    
    # 設置 preferences
    preferences = {}
    # 先設置 overpeople 的偏好
    for s in stations:
        preferences[("overpeople", s)] = -100  # overpeople 的偏好保持為負值
    
    # 設置其他人員的偏好
    preference_values = {'low': 0, 'normal': 10, 'high': 20}
    for p in personnel:
        for s in stations:
            pref = 0
            if s in p['stationSettings']:
                pref = preference_values[p['stationSettings'][s]['preference']]
            preferences[(p['id'], s)] = pref
    
    # 設置不受人數限制的工作站
    unlimited_stations = [s['id'] for s in stations_data if s.get('highPriority', False)]
    
    # 設置優先分配的工作站獎勵值
    priority_stations = {s['id']: 30 for s in stations_data if s.get('priorityAssign', False)}
    
    # 創建和求解模型
    model = LpProblem(name="scheduling", sense=LpMaximize)
    x = LpVariable.dicts("assign", [(e, s) for e in employees for s in stations], cat="Binary")
    
    # 目標函數：包含偏好值和優先分配獎勵
    model += (lpSum(preferences[e, s] * x[e, s] for e in employees for s in stations) + 
             lpSum(priority_stations.get(s, 0) * lpSum(x[e, s] for e in employees if e != "overpeople") 
                  for s in stations))
    
    # 約束條件
    # 每個人只能被分配到一個工作站
    for e in employees:
        if e != "overpeople":
            model += lpSum(x[e, s] for s in stations) == 1
    
    # 每個工作站必須有一個人（除了不受限制的工作站）
    for s in stations:
        if s not in unlimited_stations:
            model += lpSum(x[e, s] for e in employees) == 1
    
    # 人員必須有能力做該工作站
    for e in employees:
        for s in stations:
            model += x[e, s] <= capabilities[e, s]
    
    # 求解
    model.solve()
    
    # 整理結果
    assignments = []
    for e in employees:
        if e != "overpeople":  # 不包含 overpeople 在結果中
            for s in stations:
                if x[e, s].value() == 1:
                    # 找到對應的人員和工作站對象
                    person = next(p for p in personnel if p['id'] == e)
                    station = next(s_data for s_data in stations_data if s_data['id'] == s)
                    line = next(l for l in data['productionLines'] if l['id'] == station['lineId'])
                    
                    assignments.append({
                        'person': person,
                        'station': station,
                        'line': line
                    })
    
    return {
        'assignments': assignments,
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    app.run(debug=True)
