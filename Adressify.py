###
### Welcome to the fun address aggregator V0-4
###

#Import modules
import pandas as pd
import streamlit as st

import os
import requests
import time

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

pd.set_option('display.max_columns', None)

###
### Set up page
###

#remove padding
st.markdown(f""" <style>
    .reportview-container .main .block-container{{
        padding-top: 0rem;
        padding-bottom: 0rem;
    }} </style> """, unsafe_allow_html=True)

#Hide streamlit sign
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

#this is the title
st.title('Enter a New York City address')
#these are the columns
left_column, right_column = st.beta_columns([6,1])
address = left_column.text_input("")
#this is the button
right_column.text('')
right_column.text('')
pressed = right_column.button('Search')

if pressed:
    try:
        ###
        ### Ping google API
        ###

        #create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()

        #print update
        progress_bar.progress(10)
        status_text.text('Pinging Google Geocoding API...')

        #set url and api key
        api_key = os.environ.get('GOOGLE_GEO_API')
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        keys = {'address': address, 'key': api_key}

        #ping the google geocoding api
        r = requests.get(url,params=keys)
        result_dic = r.json()

        #define full address
        address = result_dic['results'][0]['formatted_address']
        #define street number
        street_number = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "street_number":
                street_number = i['long_name']
        #define street name
        street_name = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "route":
                street_name = i['long_name']
        #define neighborhood
        neighborhood = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "neighborhood":
                neighborhood = i['long_name']
        #define county
        county = "N/A"
        for i in result_dic['results'][0]['address_components']:
            for j in i['types']:
                if j == "sublocality_level_1":
                    county = i['long_name']
        #define zip code
        _zip = "N/A"
        for i in result_dic['results'][0]['address_components']:
            if i['types'][0] == "postal_code":
                _zip = i['long_name']
        #define coordinates
        latitude = result_dic['results'][0]['geometry']['location']['lat']
        longitude = result_dic['results'][0]['geometry']['location']['lng']

        ###
        ### Grab building records with Selenium 
        ###

        #set driver options (to hide the new chrome tab)
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("window-size=1400,900")
        options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")

        #print update
        progress_bar.progress(35)
        status_text.text(f'Loading building records...')

        #launch driver
        driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=options)
        #print update
        progress_bar.progress(35)
        #send driver to building records website 
        url = "http://a810-bisweb.nyc.gov/bisweb/bispi00.jsp"
        driver.get(url)

        #waiting for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "boro1"))
        )

        #print update
        progress_bar.progress(40)
        status_text.text('Grabbing building records...')

        #input borough
        select = Select(driver.find_element_by_id('boro1'))
        select.select_by_visible_text(county)
        #input street number
        street_number_input = driver.find_element_by_name('houseno')
        street_number_input.send_keys(street_number)
        #input street name
        street_name_input = driver.find_element_by_name('street')
        street_name_input.send_keys(street_name)
        #click search
        button = driver.find_element_by_xpath("/html/body/div/table[2]/tbody/tr[3]/td/table/tbody/tr/td[5]/input")
        button.click()

        #waiting for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/center/table[2]/tbody/tr[2]/td[2]"))
        )

        #grab results
        BIN = driver.find_elements_by_class_name("maininfo")[2].text.replace('BIN# ','').strip()
        record_url = f"http://a810-bisweb.nyc.gov/bisweb/PropertyProfileOverviewServlet?bin={BIN}"
        block = driver.find_elements_by_class_name("content")[5].text.replace(": ", "").strip()
        lot = driver.find_elements_by_class_name("content")[11].text.replace(": ", "").strip()
        if driver.find_element_by_xpath("/html/body/center/table[7]/tbody/tr[3]/td/b").text == "This property is not located in an area that may be affected by Tidal Wetlands, Freshwater Wetlands, Coastal Erosion Hazard Area, or Special Flood Hazard Area.":
            flood = "No"
        else:
            flood = "Yes"
        tax_building_type = driver.find_element_by_xpath("/html/body/center/table[7]/tbody/tr[5]/td[2]").text

        driver.quit()

        ###
        ### Grab financial records with Selenium
        ###

        #print update
        progress_bar.progress(65)
        status_text.text('Grabbing financial records...')

        if county == "Manhattan":
            borough_selector = "(1) Manhattan"
        elif county == "Bronx":
            borough_selector = "(2) Bronx"
        elif county == "Brooklyn":
            borough_selector = "(3) Brooklyn"
        elif county == "Queens":
            borough_selector = "(4) Queens"
        elif county == "Staten Island":
            borough_selector = "(5) Staten Island"
        else:
            print("Oh dear, that seems to have broken.")

        #launch webdriver
        driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=options)
        #send driver to finance website
        url = "https://a836-pts-access.nyc.gov/care/search/commonsearch.aspx?mode=persprop"
        driver.get(url)
        #accept terms + conditions
        button = driver.find_element_by_id("btAgree")
        button.click()

        #wait for page to load
        time.sleep(1)

        #input borough
        select = Select(driver.find_element_by_class_name('FormText'))
        select.select_by_visible_text(borough_selector)
        #input block
        block_input = driver.find_element_by_id('inpTag')
        block_input.send_keys(block)
        #input lot
        lot_input = driver.find_element_by_id('inpStat')
        lot_input.send_keys(lot)
        #click search button
        button = driver.find_element_by_id("btSearch")
        button.click()
        #click link for recent financial transactions
        button = driver.find_element_by_xpath("/html/body/div/div[3]/div/nav/div/div/li[12]")
        button.click()

        #print update
        progress_bar.progress(80)
        status_text.text('Bringing everything together...')

        #waiting for page to load
        WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div/div[3]/div/nav/div/div/li[12]"))
            )

        #grabbing fun financial data
        owner = driver.find_elements_by_class_name("DataletData")[3].text
        land_area_sqft = driver.find_elements_by_class_name("DataletData")[15].text.replace(',','')
        estimated_market_value = driver.find_elements_by_class_name("DataletData")[27].text

        #click link for tax data
        button = driver.find_element_by_xpath("/html/body/div/div[3]/div/nav/div/div/li[7]/a/span")
        button.click()

        #waiting for page to load
        WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div/div[3]/div/nav/div/div/li[12]"))
            )
        
        #grab url
        recent_tax = driver.find_element_by_xpath("/html/body/div/div[3]/section/div/form/div[3]/div/div/table/tbody/tr/td/table/tbody/tr[2]/td/div/div/table[2]/tbody/tr[2]/td[3]/a").get_attribute('href')
        
        driver.quit()

        ###
        ### Grab zip code data
        ###

        #set url
        url = 'https://data.cityofnewyork.us/resource/pri4-ifjk.json'
        r = requests.get(url)
        result_dic = r.json()
        
        for zipcode in result_dic:
            if zipcode['modzcta'] == _zip:
                zip_pop = zipcode['pop_est']
        zip_pop = "{:,}".format(int(zip_pop))

        ###
        ### Print everything useful
        ###
        
        #convert square feet into acres
        land_area_acres = round(int(land_area_sqft) / 43560, 3)

        #print update
        progress_bar.progress(100)
        status_text.text('')

        #print out results
        st.write(f"**Full address**: {address}")
        st.write(f"**Owner**: {owner}")
        st.write(f"**Estimated market value**: ${estimated_market_value}")
        st.write(f"**Tax code**: {tax_building_type}")
        st.write(f"**Land area (acres)**: {land_area_acres}")
        st.write(f"**Any flood risk**: {flood}")
        st.write(f"**Coordinates**: {latitude}, {longitude}")
        st.write(f"**Building record**: [Click here for details]({record_url})")
        st.write(f"**Recent tax record**: [Click here for details]({recent_tax})")
        st.write(f"**Zip code population**: {zip_pop}")

        ###
        ### Put it on a map
        ###

        dfMap = pd.DataFrame({'latitude':[latitude], 'longitude':[longitude]})
        st.map(dfMap, zoom=11)
    except:
        #print update
        progress_bar.progress(0)
        status_text

        st.write("Hmm, that didn't work. Here are a few ideas to get things rolling:")
        st.write("* Double check you are using an NYC address.")
        st.write("* Try a different way of writing the address (e.g. 'Columbia University Morningside' instead of 'Columbia University). The Google API is sometimes a bit picky.")
        st.write("* If Heroku or any of NYC's record websites are playing up, you might need to come back later.")
        st.write(f"* If you are getting persistent errors, please send me a [message](https://willjarrettdata.com/contact/) and I'll try to fix it.")