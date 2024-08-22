from selenium import webdriver
from axe_selenium_python import Axe

def main(url):
    driver = webdriver.Chrome()  # 브라우저 드라이버
    driver.get(url)

    axe = Axe(driver)
    axe.inject()  # axe-core 스크립트를 페이지에 삽입
    results = axe.run()  # 접근성 검사 수행
    axe.write_results(results, 'axe_report.json')

    violations = results['violations']
    print(f"{len(violations)} 개의 웹 접근성 위반")
    for violation in violations:
        print(violation['description'])
        for node in violation['nodes']:
            print(node['html'])

    driver.quit()

if __name__ == "__main__":
    url = "https://www.wa.or.kr/"  # 접근성을 검사할 웹사이트 URL 입력
    main(url)