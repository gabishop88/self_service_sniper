import requests, getpass, time, json, os
from threading import Thread
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as webcond

class ClassSniper:
    '''
    Selenium Webdriver wrapper that provides some functionalities to assist with signing up for classes.
    The goal is to be able to sign up for specific classes as soon as they are open

    functions:
     - __init__: creates a webdriver instance using open_browser and takes credentials
     - open_browser: creates and returns a chrome webdriver instance
     - navigate: browse to the given url
     - click: clicks on the specified page element
     - write: inputs text into the spefied input element, checks for stored data, such as credentials if text is a key
    '''
    data = {}

    def __init__(self, netid, password, primary_detached=False):
        self.data['registration_url'] = "https://banner.apps.uillinois.edu/StudentRegistrationSSB/?mepCode=1UIUC"
        self.data['courses_base_url'] = "https://courses.illinois.edu/schedule/2023/spring"

        self.data['netid'] = netid
        self.data['password'] = password

        self.driver = self.open_browser(primary_detached) 

    def open_browser(self, detach, wait=10.0):
        chrome_options = Options()
        chrome_options.add_experimental_option('detach', detach)
        driver = webdriver.Chrome(chrome_options=chrome_options)
        driver.implicitly_wait(wait)
        return driver

    def navigate(self, url):
        self.driver.get(url)

    def click(self, identifier, by=By.ID):
        self.driver.find_element(by, identifier).click()

    def write(self, box_identifier, text, by=By.ID): 
        '''
        Writes text into the box with the given identifier on the page. 
        If text is a key to the internal data dictionary, the value stored in the dictionary will be used instead.
        '''
        self.driver.find_element(by, box_identifier).send_keys(self.data.get(text,text))

    def find_element(self, identifier, by=By.ID):
        return self.driver.find_element(by, identifier)

    def store_data(self, key, value):
        self.data[key] = value
    
    def wait_for(self, identifier, by=By.ID, timeout=30):
        elem = WebDriverWait(self.driver, timeout).until(webcond.visibility_of(self.find_element(identifier, by)))
        return elem

    def close(self):
        self.driver.close()

def browse_to_registration(browser:ClassSniper):
    browser.navigate(browser.data['registration_url'])
    browser.click('registerLink')
    browser.write('netid', 'netid')
    browser.write('easpass', 'password')
    browser.find_element('easpass').submit()

    #TODO: maybe add some error handling here that will check to make sure the sign in was successful

    browser.click('s2id_txt_term')
    browser.click('select2-result', By.CLASS_NAME)
    browser.click('term-go')

    browser.wait_for('enterCRNs-tab')
    browser.click('enterCRNs-tab')

def register_crns(browser:ClassSniper, crn_list):
    try:
        tab = browser.find_element('tabs-enterCRN')
        correct_page = tab.is_displayed()
    except NoSuchElementException:
        correct_page = False
    if not correct_page:
        browse_to_registration(browser)

    for i,crn in enumerate(crn_list):
        browser.write(f'txt_crn{i+1}', str(crn))
        browser.click('addAnotherCRN')
    browser.click('addCRNbutton')
    # find errors?
    errors = [e.text for e in browser.driver.find_elements(By.XPATH, '//ul[@class="error-container"]//a')]
    buttons = browser.driver.find_elements(By.XPATH, '//ul[@class="error-container"]//button')

    for b in buttons: # clear any alerts
        b.click()
        notif = browser.driver.find_element(By.CLASS_NAME, 'notification-center-anchor')
        if notif.is_displayed():
            notif.click()
        
    browser.wait_for(f's2id_action-{crn_list[-1]}-ddl')
    browser.click('saveButton')
    return errors

def attempt_registration(browser:ClassSniper, classes:list):
    registration_errors = register_crns(browser, classes)
    print(*registration_errors, sep='\n')
    cannot_register_crns = [int(error.split(' ')[1]) for error in registration_errors]
    print('Removing CRN(s)', cannot_register_crns)
    [classes.remove(crn) for crn in cannot_register_crns if crn in classes]

    errors = [e.text for e in browser.driver.find_elements(By.XPATH, '//ul[@class="error-container"]//a')]
    buttons = browser.driver.find_elements(By.XPATH, '//ul[@class="error-container"]//button')
    for b in buttons: # clear any alerts
        b.click()
        notif = browser.driver.find_element(By.CLASS_NAME, 'notification-center-anchor')
        if notif.is_displayed():
            notif.click()

    print(*errors, sep='\n')
    problems = []
    for error in errors:
        divided = error.split(' ')
        crn = int(divided[3][:-1])
        if divided[4:5] != ['Closed','Section'] and crn not in problems:
            problems.append(crn)
            classes.remove(crn)
    print('Removing CRN(s)', problems)

    return classes

def monitor_classes(data):
    '''
    Given a list of CRNs, start monitoring each class to wait until it is open
    When a class opens a seat, register for it
    '''
    browser = ClassSniper(data["netid"], data["password"])
    browse_to_registration(browser)
    classes = data['classes']

    print('before', classes)
    classes = attempt_registration(browser, classes) # TODO: Remove classes that successfully signed up, also loop this to continue trying on closed sections.
    print('after', classes)

    print('done!')
    while True: 
        pass

def main():
    # netid = input('Enter your netid: ')
    # passw = getpass.getpass('Password: ')

    # classes = []
    # crn = None
    # while crn != "":
    #     crn = input('Enter a CRN: ')
    #     classes.append(crn)

    # To work properly, personal_info.json must contain 'netid', 'password', and 'classes'. classes is a list of objects that each contain 'Subject', 'Number', and 'CRN'.
    # TODO: create a command line interface or smth to generate this file or take in the file name
    
    data = dict()
    with open("personal_info.json", 'r') as f:
        data = dict(json.load(f))
    
    monitor_classes(data)

    
if __name__ == '__main__':
    main()