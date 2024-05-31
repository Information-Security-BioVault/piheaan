from flask import Flask, request, jsonify, redirect, url_for
from dtw_server import Server
from dtw_client import Client
import threading

app = Flask(__name__)

server = Server()

# 등록 라우터
@app.route('/api/register', methods=['POST'])
async def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    """
    기존에는 클라이언트 측에서 pi-heaan 모듈로 암호화된 데이터 및 계산에 필요한 객체를 전송하는 방식으로 구상했으나,
    코틀린과 pi-heaan 모듈 간 호환문제로 인해 클라이언트에서 정상적으로 보냈다고 가정하고 실제로는 서버에서 처리하도록 구현함
    """
    timeseries = data.get('data')
    watch_id = data.get('id')
    # eval_ = data.get('eval') # 제거
    # args = data.get('args') # 제거
    client = Client(watch_id) # 추가
    client.create_keys() # 추가
    client.load_keys() # 추가
    client.set_args() # 추가
    timeseries = [await client.encrypt(data_) for data_ in timeseries[:2]] # 추가
    
    # 데이터 저장
    server.save_eval(watch_id, client.eval)
    server.save_data(watch_id, timeseries)
    server.save_args(watch_id, client.args)
    
    # 응답
    response = {
        'message': '사용자 등록 성공',
        'watch_id': watch_id
    }
    return jsonify(response)

# 인증 라우터
@app.route('/api/authenticate', methods=['POST'])
async def authenticate():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    """
    기존에는 pi-heaan으로 암호화된 데이터를 클라이언트 측에서 전송하는 방식으로 구상했으나,
    코틀린과 pi-heaan 모듈 간 호환문제로 인해 클라이언트에서 정상적으로 보냈다고 가정하고 실제로는 서버에서 처리하도록 구현함
    """
    watch_id = data.get('id')
    input_data = data.get('data')
    client = Client(watch_id) # 추가
    client.load_keys() # 추가
    input_data = await client.encrypt(input_data) # 추가
    
    # 데이터 불러오기
    data = server.load_data(watch_id)
    eval_ = server.load_eval(watch_id)
    args = server.load_args(watch_id)
    
    # 인증 수행
    encrypted_result = await server.identification(watch_id, input_data)
    
    # 복호화
    """
    기존에는 암호화된 결과를 클라이언트 측에서 복호화하는 방식으로 구상했으나,
    코틀린과 pi-heaan 모듈 간 호환문제로 인해 클라이언트에서 복호화하는 것이 불가능하므로 서버에서 처리하도록 구현함
    """
    result = await client.check_result(encrypted_result) # 추가

    # 응답
    response = {
        'message': '인증 결과 반환',
        'watch_id': watch_id,
        'result': result,
        'validation_code': client.validation_code # 추가: 파일 잠금 및 해제를 위한 코드(기존에는 클라이언트에서 처리)
    }
    return jsonify(response)

# 파일 잠금 라우터
@app.route('/api/lock', methods=['POST'])
def lock():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    watch_id = data.get('id')
    code = data.get('validation_code')
    
    # 파일 잠금
    if not server.lock_file(watch_id, code):
        return jsonify({'error': '인증 실패'}), 400
    
    # 응답
    response = {
        'message': '파일 잠금 성공',
        'watch_id': watch_id
    }
    return jsonify(response)

# 파일 잠금 해제 라우터
@app.route('/api/unlock', methods=['POST'])
def unlock():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    watch_id = data.get('id')
    code = data.get('validation_code')
    
    # 파일 잠금 해제
    if not server.unlock_file(watch_id, code):
        return jsonify({'error': '인증 실패'}), 400
    
    # 응답
    response = {
        'message': '파일 잠금 해제 성공',
        'watch_id': watch_id
    }
    return jsonify(response)

# 파일 잠금 상태 확인
@app.route('/api/request_authority', methods=['POST'])
def request_authority():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    watch_id = data.get('id')
    
    # 파일 잠금 상태 확인
    lock_status = server.lock_status[watch_id]
    
    # 응답
    if lock_status:
        return jsonify({'message': '파일 잠금 상태입니다.'}), 400
    else:
        return jsonify({'message': '파일 잠금 해제 상태입니다.'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

