import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
import schedule
import datetime
import time
import pyttsx3
import speech_recognition as sr

engine = pyttsx3.init()
engine.setProperty("rate", 170)  # speed
engine.setProperty("volume", 1)  # max volume

def speak(text):
    print(text)
    engine.say(text)
    engine.runAndWait()

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        speak("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
    try:
        query = recognizer.recognize_google(audio)
        speak(f"You said: {query}")
        return query
    except sr.UnknownValueError:
        speak("Sorry, I could not understand. Please try again.")
        return listen()
    except sr.RequestError:
        speak("Speech recognition service is unavailable.")
        return ""

# -------------------------
# Scraper Function
# -------------------------
def scrape_indeed(roles, location, voice=False):
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/117.0.0.0 Safari/537.36")

    driver = uc.Chrome(options=options)
    all_jobs = []

    for role in roles:
        role_encoded = urllib.parse.quote(role)
        location_encoded = urllib.parse.quote(location)

        search_url = f"https://in.indeed.com/jobs?q={role_encoded}&l={location_encoded}"
        msg = f"Searching {role} in {location}"
        speak(msg) if voice else print(msg)

        driver.get(search_url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
            )
        except:
            msg = f"No jobs found for {role} in {location} (timeout or blocked)"
            speak(msg) if voice else print(msg)
            continue

        # scroll to load more
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
        msg = f"Found {len(job_cards)} job cards for {role} in {location}"
        speak(msg) if voice else print(msg)

        for job in job_cards:
            try:
                title = job.find_element(By.CSS_SELECTOR, "h2.jobTitle span").text.strip()
            except:
                title = "N/A"
            try:
                company = job.find_element(By.CSS_SELECTOR, "span[data-testid='company-name']").text.strip()
            except:
                company = "N/A"
            try:
                job_location = job.find_element(By.CSS_SELECTOR, "div[data-testid='text-location']").text.strip()
            except:
                job_location = location
            try:
                link = job.find_element(By.CSS_SELECTOR, "h2.jobTitle a").get_attribute("href")
            except:
                link = "N/A"

            all_jobs.append({
                "Title": title,
                "Company": company,
                "Location": job_location,
                "Role": role,
                "Link": link,
                "Scraped On": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    driver.quit()

    df = pd.DataFrame(all_jobs)
    if not df.empty:
        try:
            old_df = pd.read_csv("indeed_jobs.csv")
            df = pd.concat([old_df, df], ignore_index=True)
        except FileNotFoundError:
            pass
        df.to_csv("indeed_jobs.csv", index=False, encoding="utf-8")

        msg = f"Scraped {len(all_jobs)} jobs. Updated indeed_jobs.csv"
        speak(msg) if voice else print(msg)
    else:
        msg = "No jobs scraped. Check selectors or location spelling."
        speak(msg) if voice else print(msg)

# -------------------------
# Main Program
# -------------------------
print("Choose Mode:")
print("1. Text Mode")
print("2. Voice Mode")
mode = input("Enter choice (1/2): ")

voice_mode = False

if mode == "1":
    roles_input = input("Enter job roles (comma separated): ")
    roles = [r.strip() for r in roles_input.split(",")]
    location = input("Enter job location: ")

elif mode == "2":
    voice_mode = True
    speak("Please say the job roles you want to search.")
    roles_input = listen()
    roles = [r.strip() for r in roles_input.split(",")]

    speak("Please say the job location.")
    location = listen()

def job_task():
    msg = "Running Indeed scraper now..."
    speak(msg) if voice_mode else print(msg)
    scrape_indeed(roles, location, voice=voice_mode)
    msg = "Task finished."
    speak(msg) if voice_mode else print(msg)

job_task()

schedule.every().day.at("09:00").do(job_task)

msg = "Scheduler started. Scraper will run daily at 9 AM."
speak(msg) if voice_mode else print(msg)

while True:
    schedule.run_pending()
    time.sleep(60)
