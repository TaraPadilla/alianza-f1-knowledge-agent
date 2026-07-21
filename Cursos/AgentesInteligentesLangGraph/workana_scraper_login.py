from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


URL = "https://www.workana.com/es/login"
SEARCH_URL = "https://www.workana.com/jobs?category=it-programming&has_few_bids=1&language=es&publication=1d&skills=amazon-web-services%2Cangular%2Cartificial-intelligence%2Ccss3%2Cdata-modeling%2Cfuncional-analysis%2Chtml%2Cjava%2Cjavascript%2Claravel%2Cmicrosoft-excel%2Cmobile-app-design-1%2Cmysql%2Coperations-management%2Cpaypal%2Cphp%2Cpower-bi%2Creact-js%2Cseo-1%2Cspring-boot%2Csql%2Csql-server%2Cvisual-basic%2Cweb-services%2Cwordpress%2Cdelphi%2Cnode-js%2Cuml-design%2Cvba"
EMAIL_INPUT_ID = "email-input"
PASSWORD_INPUT_ID = "password-input"
EMAIL_USER = "daalejito20@gmail.com"
PASSWORD_USER = "ChHRfsF98QLv_g%"

SUCCESS_TEXTS = [
    "mis proyectos",
    "dashboard",
    "mis trabajos",
    "cerrar sesión",
    "mi perfil",
    "workana"
]

ERROR_TEXTS = [
    "credenciales",
    "email o contraseña",
    "incorrect",
    "error",
    "intenta nuevamente",
    "verify your account",
    "captcha"
]


def build_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=chrome_options)


def login_result(driver, wait):
    try:
        wait.until(lambda d: (
            "/login" not in d.current_url.lower()
            or len(d.find_elements(By.ID, EMAIL_INPUT_ID)) == 0
            or any(text in d.page_source.lower() for text in ERROR_TEXTS)
        ))
    except Exception:
        pass

    current_url = driver.current_url.lower()
    page_source = driver.page_source.lower()
    body_text = " ".join(driver.find_elements(By.TAG_NAME, "body")[0].text.lower().split())

    login_success = (
        "/login" not in current_url
        and len(driver.find_elements(By.ID, EMAIL_INPUT_ID)) == 0
        and len(driver.find_elements(By.ID, PASSWORD_INPUT_ID)) == 0
    )

    if login_success:
        print("✅ Login exitoso: la sesión quedó abierta en Workana.")
        return True

    if any(text in body_text for text in ERROR_TEXTS):
        print("❌ Login fallido: la página mostró un error de credenciales o validación.")
        return False

    if any(text in page_source for text in SUCCESS_TEXTS):
        print("✅ Login exitoso: se detectó la vista autenticada de Workana.")
        return True

    print("❌ Login fallido: no se detectó una sesión abierta después del intento.")
    return False


def main():
    driver = build_driver()
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(URL)

        email_input = wait.until(EC.presence_of_element_located((By.ID, EMAIL_INPUT_ID)))
        password_input = wait.until(EC.presence_of_element_located((By.ID, PASSWORD_INPUT_ID)))

        email_input.clear()
        email_input.send_keys(EMAIL_USER)

        password_input.clear()
        password_input.send_keys(PASSWORD_USER)

        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        if login_result(driver, wait):
            driver.get(SEARCH_URL)
            wait.until(EC.url_contains("workana.com/jobs"))
            print("✅ Navegación a la búsqueda realizada correctamente.")
        else:
            print("❌ No fue posible navegar a la búsqueda porque el login falló.")

    except Exception as exc:
        print(f"❌ Ocurrió un error durante el login: {exc}")

    finally:
        input("Presione Enter para cerrar el navegador...")
        driver.quit()


if __name__ == "__main__":
    main()
