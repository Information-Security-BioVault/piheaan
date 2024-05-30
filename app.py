from flask import Flask, request, jsonify, redirect, url_for
from dtw_server import Server

app = Flask(__name__)

server = Server()

# 등록 라우터
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    data = data.get('data')
    eval_ = data.get('eval')
    args = data.get('args')
    watch_id = data.get('id')
    
    # 데이터 저장
    server.save_eval(watch_id, eval_)
    server.save_data(watch_id, data)
    server.save_args(watch_id, args)
    
    # 응답
    response = {
        'message': '사용자 등록 성공',
        'watch_id': watch_id
    }
    return jsonify(response)

# 인증 라우터
@app.route('/api/authenticate', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON 데이터가 필요합니다.'}), 400
    
    # 데이터 추출
    input_data = data.get('data')
    watch_id = data.get('id')
    
    # 데이터 불러오기
    data = server.load_data(watch_id)
    eval_ = server.load_eval(watch_id)
    args = server.load_args(watch_id)
    
    # 인증 수행
    encrypted_result = server.identification(watch_id, input_data)
    result = server.check_result(encrypted_result)
    
    # 응답
    response = {
        'message': '인증 결과 반환',
        'watch_id': watch_id,
        'result': result
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
    if not server.lock(watch_id, code):
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
    if not server.unlock(watch_id, code):
        return jsonify({'error': '인증 실패'}), 400
    
    # 응답
    response = {
        'message': '파일 잠금 해제 성공',
        'watch_id': watch_id
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

