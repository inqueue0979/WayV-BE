from flask import Flask, request, jsonify
from selenium import webdriver
from axe_selenium_python import Axe
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def run_axe(url):
    # Chrome WebDriver를 사용하여 브라우저를 열고 URL 로드
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        options=options
    )
    driver.get(url)

    # axe-core 스크립트를 삽입하고 접근성 검사 수행
    axe = Axe(driver)
    axe.inject()
    results = axe.run()
    
    # WebDriver 종료
    driver.quit()
    
    # 결과 반환
    return results['violations']

@app.route('/check-accessibility', methods=['GET'])
def check_accessibility():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400
    
    try:
        violations = run_axe(url)
        return jsonify({"violations": violations}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def Hello():
    return 'WayV WA Server | 0822:0940'

if __name__ == '__main__':
    app.run(host='0.0.0.0')