import pandas as pd
import re
from datetime import date, timedelta
import readpdf_data

def preprocess_data(rawdata):
    rawdata.rename(columns={"Account Name:": "Account_Name", "Date & Time": "Date_Time", "Activity Details": "Activity_Details", "Amount ($ / Meals)": "Amount"}, inplace=True)
    rawdata['Date_Time'] = pd.to_datetime(rawdata['Date_Time'])
    rawdata = rawdata[rawdata['Activity_Details'] != 'Meal Plan Office']
    rawdata.reset_index(drop=True, inplace=True)
    return rawdata

def filter_mealswipes(rawdata):
    alldininghalls = ["HampDC1", "HampDC2", "HampDC3", "HampDC4", "BerkDC1", "BerkDC2", "BerkDC3", "BerkDC4",
                      "FrankDC1", "FrankDC2", "FrankDC3", "FrankDC4", "WorcDC1", "WorcDC2", "WorcDC3", "WorcDC4"]

    if (rawdata['Account_Name'] == "E Unlimited 250").any() or (rawdata['Account_Name'] == "M Unlimited DC").any():
        mealswipes = rawdata[rawdata['Account_Name'].isin(["E Unlimited 250", "M Unlimited DC"])]
    else:
        mealswipes = rawdata[rawdata['Activity_Details'].isin(alldininghalls)]

    mealswipes = mealswipes[mealswipes['Activity_Details'] != "Meal Plan Office"]
    mealswipes.loc[:, 'Balance'] = mealswipes['Balance'].str.replace('$', '')
    mealswipes['Balance'] = pd.to_numeric(mealswipes['Balance'])
    mealswipes.reset_index(drop=True, inplace=True)
    return mealswipes

def process_mealswipes(mealswipes):
    dining_halls = ["HampDC1", "HampDC2", "HampDC3", "HampDC4", "BerkDC1", "BerkDC2", "BerkDC3", "BerkDC4",
                    "FrankDC1", "FrankDC2", "FrankDC3", "FrankDC4", "WorcDC1", "WorcDC2", "WorcDC3", "WorcDC4"]

    proccessed_meal_swipe_data = pd.DataFrame()

    for hall in dining_halls:
        hall_data = mealswipes[mealswipes['Activity_Details'].isin([hall])]
        breakfast = len(hall_data[hall_data['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
        lunch = len(hall_data[(hall_data['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (hall_data['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
        dinner = len(hall_data[(hall_data['Date_Time'].dt.time >= pd.to_datetime('16:30').time())])
        total_visits = len(hall_data)
        proccessed_meal_swipe_data[hall] = [breakfast, lunch, dinner, 'NA', total_visits]

    proccessed_meal_swipe_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner", 3: "Late_Night", 4: "Total"},
                                      inplace=True)

    return proccessed_meal_swipe_data

def process_dining_dollars(rawdata):
    alldininghalls = ["HampDC1", "HampDC2", "HampDC3", "HampDC4", "BerkDC1", "BerkDC2", "BerkDC3", "BerkDC4",
                      "FrankDC1", "FrankDC2", "FrankDC3", "FrankDC4", "WorcDC1", "WorcDC2", "WorcDC3", "WorcDC4"]

    dining_dollars = rawdata[rawdata['Account_Name'].isin(["UMass Dining Dollars", "C Basic Plan", "Student Debit Plan"])]
    dining_dollars = dining_dollars[~dining_dollars['Activity_Details'].isin(alldininghalls)]
    pattern = r'[0-9]'
    dining_dollars.loc[:, 'Amount'] = dining_dollars['Amount'].str.replace('$', '')
    dining_dollars.loc[:, 'Amount'] = dining_dollars['Amount'].str.replace('-', '')
    dining_dollars.loc[:, 'Activity_Details'] = dining_dollars['Activity_Details'].apply(lambda x: re.sub(pattern, '', str(x)))
    dining_dollars.loc[:, 'Activity_Details'] = dining_dollars['Activity_Details'].str.strip()
    dining_dollars.loc[:, 'Amount'] = pd.to_numeric(dining_dollars['Amount'])

    proccessed_dining_dolla_data = pd.DataFrame()
    mics_columns = dining_dollars['Activity_Details'].unique()

    for place in mics_columns:
        micsdf = dining_dollars[dining_dollars['Activity_Details'].isin([place])]
        num_breakfast = len(micsdf[micsdf['Date_Time'].dt.time < pd.to_datetime('11:00').time()])
        num_lunch = len(micsdf[(micsdf['Date_Time'].dt.time >= pd.to_datetime('11:00').time()) & (micsdf['Date_Time'].dt.time < pd.to_datetime('16:30').time())])
        num_dinner = len(micsdf[micsdf['Date_Time'].dt.time >= pd.to_datetime('16:30').time()])
        allsum = micsdf['Amount'].sum()
        if (micsdf['Account_Name'] == "C Basic Plan").any():
            allsum *= 12
        proccessed_dining_dolla_data[place] = [num_breakfast, num_lunch, num_dinner, len(micsdf), f"${format(allsum, '.2f')}"]

    proccessed_dining_dolla_data.rename(index={0: "Breakfast", 1: "Lunch", 2: "Dinner", 3: "Total", 4: "Total $ Spent"},
                                        inplace=True)
    return proccessed_dining_dolla_data

def main():
    rawdata = readpdf_data.returndata()
    rawdata = preprocess_data(rawdata)
    
    mealswipes = filter_mealswipes(rawdata)
    proccessed_meal_swipe_data = process_mealswipes(mealswipes)
    
    dining_dollars_data = process_dining_dollars(rawdata)

    print(f"You have gone to hamp {proccessed_meal_swipe_data['Hamp']['Total']} times")
    print(f"You have gone to berk {proccessed_meal_swipe_data['Berk']['Total']} times")
    print(f"You have gone to frank {proccessed_meal_swipe_data['Frank']['Total']} times")
    print(f"You have gone to woo {proccessed_meal_swipe_data['Woo']['Total']} times")
    print(f"you've used {len(mealswipes)} meal swipes")


if __name__ == "__main__":
    main()
