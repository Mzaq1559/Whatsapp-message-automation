from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time

driver = webdriver.Chrome()

driver.get("https://web.whatsapp.com")
repeat_count = int(input("How many times do you want to send the message? ").strip())
message = input("Enter the message you want to send: ").strip()

print("\n📷 Scan the QR code in WhatsApp Web manually if needed.")
input("📋 After scanning QR code AND opening the correct chat, press ENTER to continue...")

# Find the message box
msg_box = wait(driver, 30).until(
    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
)

# Sending the message
for _ in range(repeat_count):
    msg_box.send_keys(message)
    msg_box.send_keys(Keys.ENTER)
    # time.sleep(0.005)  # Optional delay to look more human
