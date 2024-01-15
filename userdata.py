from getorganizeddata import getdata
import pandas as pd

class Userdata:

    def __init__(self) -> None:
        self.mealswipedata, self.diningdollardata = getdata()
        self.mealswipedata.rename(columns={'HampDC': 'Hamp', 'WorcDC' : 'Worcester', 'FrankDC' : 'Frank','BerkDC' : 'Berk'}, inplace=True)

    def getTotalMealSwipesUsed(self):
        return self.mealswipedata.iloc[5].sum(axis = 0) 
    
    def getTotalMoneyUsed(self):

        return f"${'{:.2f}'.format(self.diningdollardata.iloc[4].sum(axis = 0))}"
    
    def getFavoriteDiningHall(self):
        dininghall = self.mealswipedata.iloc[-1].idxmax()
        return dininghall
    
    def getFavoriteDiningDollar(self):
        vendor = self.diningdollardata.iloc[-1].idxmax()
        moneyspent = self.diningdollardata[vendor]['Total $ Spent']
        return vendor, moneyspent
    
    def getOrderedDiningHallData(self):
        sortedDC = self.mealswipedata.iloc[-1].sort_values(ascending=False)
        sortedDC = sortedDC.loc[['Berk','Hamp','Frank','Worcester']]
        sortedDC.sort_values(ascending=False,inplace=True)
        return sortedDC
    
    def getOrderedDiningDollarData(self):
        sortedDD = self.diningdollardata.iloc[-1].sort_values(ascending=False)
        sortedDD.sort_values(ascending=False,inplace=True)

        return sortedDD

    
    def getRawMealSwipes(self):
        return self.mealswipedata
    
    def getRawDiningDollar(self):
        return self.diningdollardata
    
    def getDDtable(self):
        table = self.diningdollardata.copy()
        table.iloc[-1] = table.iloc[-1].astype(str).apply(lambda x: f"${'{:.2f}'.format(float(x))}")
        table.iloc[:-1] = table.iloc[:-1].map(lambda x : int(x))
        return table


    def getPersonality(self):
        if(self.diningdollardata.shape[1]>15):
            return "Connoisseur", "connoisseur", "You've went to ALOT of dining vendors this semester. Honestly good for you! idk if i could do that like how do you go to so many places."
        elif(self.mealswipedata['Frank']['Total']>125):
            return "Frank Enjoyer", "frankEnjoyer", "So you like frank huh."
        elif(self.diningdollardata.iloc[4].sum(axis = 0)>250):
            return "Big Spender", "bigSpender", "You've spent ALOT of money this semester on blue wall. I really don't this the dining hall food is that bad"
        elif(self.getTotalMealSwipesUsed()> 300):
            return "Calorie Consumer", "calorieConsumer", "So you really really like dining hall food. You've been there so many times you can practically live there."
        elif(self.mealswipedata['Worcester']['Total']>40 and self.mealswipedata['Hamp']['Total']>40 and self.mealswipedata['Berk']['Total']>40 and self.mealswipedata['Frank']['Total']>40):
            return "Voyager", "voyager", "You love every dining hall huh. You're probably a little indecisive, or just want to share your love to every dining hall. You must also walk a shit ton holy god."
        elif(self.mealswipedata['Worcester']['GrabNGo'] + self.mealswipedata['Frank']['GrabNGo']> 100):
            return "Quick Eater", "quickEater", "Either you're always rushing to class, or just hate finding a seat at the dining hall, you just love that grab n go. It is really good though tbh. Frank fil a chicken sanwiches are soooo good."
        elif(self.mealswipedata.iloc[0].sum()>100):
            return "Early Bird", "earlyBird", "You probrobly go to sleep at 10 every night. Good for you. I personally could never but whatever get that bag. Or you just get no sleep at all. Probably the latter."
        elif(self.mealswipedata['Worcester']['Late_Night'] + self.mealswipedata['Berk']['Late_Night']> 75):
            return "Vampire", "vampire", "Now you love the late night and waiting in line forever for some medicore food. Unless its the perogis. Or the sweet n sour chicken. Or honestly its not that bad but the lines make it bad. Why you up eating anyway go to sleep."
        else:
            return "Average Joe", "averageJoe", "You're just an average umass dining enjoyer, nothing to be ashamed of. I didn't make that many personalties and its kinda hard to get some of them so my fault. But maybe you'll get a different personality next semester :p."