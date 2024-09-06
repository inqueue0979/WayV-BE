from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from flask_cors import CORS
import re

app = Flask(__name__)
CORS(app)

# Chromedriver 설정
options = Options()
options.add_argument("--headless")  # Headless 모드 사용
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

# Chromedriver의 경로를 서비스로 설정
service = Service()  # Chromedriver 설치 경로

# 비디오 접근성 검사 엔드포인트
@app.route('/video_caption', methods=['GET'])
def video_caption():
    url = request.args.get('url', '')  # 요청 시 URL 파라미터 받기
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400

    driver = None  # 드라이버 초기화
    try:
        # Chrome WebDriver 설정
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        driver.implicitly_wait(3)

        videos = driver.find_elements(By.TAG_NAME, 'video')
        results = []

        if videos:
            for index, video in enumerate(videos, start=1):
                video_info = {"index": index}

                # 영상 썸네일 URL
                video_info["thumbnail"] = video.get_attribute('poster') if video.get_attribute('poster') else "썸네일 없음"

                # 텍스트 대본 확인
                try:
                    transcript = video.find_element(By.XPATH, "following-sibling::div[contains(@class, 'transcript')]")
                    video_info["transcript"] = "텍스트 대본이 있습니다."
                except:
                    video_info["transcript"] = "텍스트 대본이 없습니다."

                # 오디오 설명 확인
                try:
                    audio_description = video.find_element(By.XPATH, "following-sibling::audio[contains(@class, 'audio-description')]")
                    video_info["audio"] = "오디오 설명이 있습니다."
                except:
                    video_info["audio"] = "오디오 설명이 없습니다."

                # 비디오 플레이어 접근성 확인
                try:
                    if video.get_attribute("tabindex") is not None:
                        video_info["keyboard_access"] = "키보드로 접근 가능합니다."
                    else:
                        video_info["keyboard_access"] = "키보드로 접근할 수 없습니다."
                except:
                    video_info["keyboard_access"] = "키보드 접근성 확인 중 오류가 발생했습니다."

                # 스크린 리더 호환성 확인 (ARIA 속성)
                try:
                    aria_labels = video.find_elements(By.XPATH, "ancestor::*[@aria-label or @role]")
                    video_info["screen_reader"] = "ARIA 라벨이 있습니다." if aria_labels else "ARIA 라벨이 없습니다."
                except:
                    video_info["screen_reader"] = "ARIA 라벨 확인 중 오류가 발생했습니다."

                results.append(video_info)
        else:
            results.append({"message": "페이지에 영상이 없습니다."})

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver is not None:
            driver.quit()

# 명도 대비 계산 함수
def calculate_contrast_ratio(fg_color, bg_color):
    # RGB 문자열에서 숫자 추출 및 안전 처리
    def parse_rgb(color):
        try:
            # rgba 형식 및 다른 형식을 처리하기 위해
            rgb = list(map(int, re.findall(r'\d+', color)))
            if len(rgb) == 4:  # RGBA 형식일 경우, 투명도 값 제거
                rgb = rgb[:3]
            if len(rgb) != 3:  # 잘못된 형식의 경우 기본 색상 반환
                return [0, 0, 0]  # 검정색 기본값
            return rgb
        except:
            return [0, 0, 0]  # 예외 발생 시 기본값 (검정색)

    fg = parse_rgb(fg_color)
    bg = parse_rgb(bg_color)

    # 명도 계산
    def luminance(rgb):
        r, g, b = [v / 255.0 for v in rgb]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    l1 = luminance(fg) + 0.05
    l2 = luminance(bg) + 0.05
    return max(l1, l2) / min(l1, l2)

# 명도 대비 확인
@app.route('/contrast', methods=['GET'])
def contrast():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "URL 파라미터가 누락되었습니다"}), 400

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        driver.implicitly_wait(3)

        elements = driver.find_elements(By.XPATH, '//*[text()]')  # 텍스트가 있는 모든 요소 찾기
        results = []

        for element in elements:
            fg_color = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).color;", element)
            bg_color = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).backgroundColor;", element)
            contrast_ratio = calculate_contrast_ratio(fg_color, bg_color)
            results.append({
                "text": element.text,
                "foreground_color": fg_color,
                "background_color": bg_color,
                "contrast_ratio": contrast_ratio,
                "wcag_compliant": contrast_ratio >= 4.5  # WCAG AA 기준 적용
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver:
            driver.quit()

# 키보드 사용 보장
@app.route('/keyboard', methods=['GET'])
def keyboard():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        driver.implicitly_wait(3)

        # 키보드로 접근 가능한 요소들만 선택
        focusable_elements = driver.find_elements(By.XPATH, "//a | //button | //input | //textarea | //select | //div[@tabindex] | //span[@tabindex]")
        results = []

        accessible_count = 0
        total_elements = len(focusable_elements)

        for element in focusable_elements:
            tag_name = element.tag_name
            accessible = element.is_displayed() and element.is_enabled()
            if accessible:
                accessible_count += 1

            results.append({
                "element": tag_name,
                "accessible": accessible,
                "message": "키보드 접근 가능" if accessible else "키보드 접근 불가"
            })

        # 접근 가능 항목 퍼센트 계산
        accessible_percentage = (accessible_count / total_elements) * 100 if total_elements > 0 else 0

        # 결과에 퍼센트 추가
        summary = {
            "total_elements": total_elements,
            "accessible_count": accessible_count,
            "accessible_percentage": round(accessible_percentage, 2)  # 소수점 둘째 자리까지 반올림
        }

        return jsonify({"results": results, "summary": summary})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver is not None:
            driver.quit()

# 초점 이동 확인
@app.route('/focus', methods=['GET'])
def focus():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        driver.implicitly_wait(3)

        # 포커스 가능한 모든 요소를 찾음
        focusable_elements = driver.find_elements(By.XPATH, "//*[@tabindex >= 0] | //a | //button | //input | //textarea | //select")
        results = []

        for element in focusable_elements:
            element.click()
            active_element = driver.switch_to.active_element
            results.append({
                "element": element.tag_name,
                "focused": active_element == element,
                "message": "초점 이동 성공" if active_element == element else "초점 이동 실패"
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver is not None:
            driver.quit()

# 표의 구성 확인
@app.route('/table_structure', methods=['GET'])
def table_structure():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        driver.implicitly_wait(3)

        tables = driver.find_elements(By.TAG_NAME, 'table')
        results = []

        for table in tables:
            headers = table.find_elements(By.TAG_NAME, 'th')
            rows = table.find_elements(By.TAG_NAME, 'tr')
            results.append({
                "headers": len(headers),
                "rows": len(rows),
                "message": "표 구성 확인 완료" if headers and rows else "표 구성 오류"
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver is not None:
            driver.quit()

# 레이블 제공 확인
@app.route('/label', methods=['GET'])
def label():
    url = request.args.get('url', '')
    if not url:
        return jsonify({"error": "URL 파라미터가 필요합니다."}), 400

    driver = None
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        driver.implicitly_wait(3)

        inputs = driver.find_elements(By.XPATH, "//input | //select | //textarea")
        results = []

        for input_element in inputs:
            label = driver.execute_script(
                "return document.querySelector('label[for=\"" + input_element.get_attribute('id') + "\"]');"
            )
            results.append({
                "input_type": input_element.tag_name,
                "label_present": bool(label),
                "message": "레이블이 제공되었습니다." if label else "레이블이 제공되지 않았습니다."
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if driver is not None:
            driver.quit()

@app.route('/')
def hello():
    return 'WayV WA Server | 0822:0940'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500)