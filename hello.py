from flask import Flask, render_template, redirect, url_for
from waitress import serve
import pandas as pd
import userdata

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html")

@app.route("/hello_world", methods=["POST"])
def hello_world():
    user = userdata.Userdata()
    topDcs = user.getOrderedDiningHallData()
    topDDs = user.getOrderedDiningDollarData()
    poop = user.getRawMealSwipes()
    pee = user.getRawDiningDollar()
    return render_template(
        "index.html",
        hamp = poop['Hamp']['Total'],
        worc = poop['Worcster']['Total'],
        frank = poop['Frank']['Total'],
        berk = poop['Berk']['Total'],
        favDc = topDcs.index[0],
        favBrk = poop[topDcs.index[0]]['Breakfast'],
        favLun = poop[topDcs.index[0]]['Lunch'],
        favDin = poop[topDcs.index[0]]['Dinner'],
        favLaN = poop[topDcs.index[0]]['Late_Night'],
        first_DC_Name = topDcs.index[0],
        first_DC_Total = topDcs.iloc[0],
        second_DC_Name = topDcs.index[1],
        second_DC_Total = topDcs.iloc[1],
        third_DC_Name = topDcs.index[2],
        third_DC_Total = topDcs.iloc[2],
        fourth_DC_Name = topDcs.index[3],
        fourth_DC_Total = topDcs.iloc[3],

        first_DD_Name = topDDs.index[0],
        first_DD_Total = topDDs.iloc[0],
        first_DD_Dollars = '{:.2f}'.format(pee[topDDs.index[0]]['Total $ Spent']),
        second_DD_Name = topDDs.index[1],
        second_DD_Total = topDDs.iloc[1],
        second_DD_Dollars = '{:.2f}'.format(pee[topDDs.index[1]]['Total $ Spent']),
        third_DD_Name = topDDs.index[2],
        third_DD_Total = topDDs.iloc[2],
        third_DD_Dollars = '{:.2f}'.format(pee[topDDs.index[2]]['Total $ Spent']),
        totalMealSwipes = user.getTotalMealSwipesUsed(),
        totalDiningDollars = user.getTotalMoneyUsed()



        )
@app.route("/test")
def test():
    user = userdata.Userdata()
    topDcs = user.getOrderedDiningHallData()
    topDDs = user.getOrderedDiningDollarData()
    poop = user.getRawMealSwipes()
    pee = user.getRawDiningDollar()
    personality, personalityImg, personalityBlurb = user.getPersonality()
    return render_template(
        "test.html",


        totalMealSwipes = user.getTotalMealSwipesUsed(),
        totalDiningDollars = user.getTotalMoneyUsed(),
        topDCs = topDcs,
        topDDs = topDDs,
        rawmealswipes = poop,
        rawdiningdollar = pee,
        DCtables=[poop.to_html(classes='data', header="true")],
        DDtables=[user.getDDtable().to_html(classes='data', header="true")],
        personality = personality,
        personalityImg = personalityImg,
        personalityBlurb = personalityBlurb



        )



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)