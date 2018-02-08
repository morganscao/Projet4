from flask import Flask, render_template, request
#from config import Config
import pickle
import datetime
import pandas as pd
from sklearn.externals import joblib
import os

app = Flask(__name__)

app.config.from_object('config')

CT_DIR = app.config['BASESAVE']
print(CT_DIR)
def load_obj(name):
    with open(os.path.join(CT_DIR, name + '.pkl'), 'rb') as f:
        return pickle.load(f)

# Liste des aéroports
model_airport = load_obj('model_airport')
choices_airport = model_airport.get_values()
# Liste des companies
model_carrier = load_obj('model_carrier')
choices_carrier = [(x, x) for x in model_carrier]

if len(model_carrier) > 0:
    print("model_carrier OK")

CT_COMPANY = "company"
CT_DEPARTURE = "departure"
CT_DATE = "date"
CT_TIME = "time"

# Liste des jours fériés américains en  2016
holidays = ['2016-01-01', '2016-01-18', '2016-02-15', '2016-05-30', '2016-07-04', '2016-09-05', '2016-10-10', '2016-11-11', '2016-11-24', '2016-12-26']
dfhol = pd.DataFrame({'date' : holidays}, columns = ['date'])
dfhol = pd.to_datetime(dfhol.date)

def DaysToHoliday(dt):
    if dt.year != 2016:
        # On renvoie une valeur moyenne si on n'est pas en 2016
        return 10
    dd = datetime.datetime(2016, dt.month, dt.day)
    return (dfhol - dd).abs().min().days


@app.route('/')
def index():
    # Affichage de la page d'accueil avec les aéroports et les compagnies
    return render_template('index.html', airports=choices_airport, companies=choices_carrier)

@app.route('/predict/', methods=['POST'])
def hello():
    if request.method == 'POST':
        try:
            # Récupoération des paramètres envoyés par la requête
            myCOMPANY = request.values[CT_COMPANY]
            myDEPARTURE = request.values[CT_DEPARTURE]
            myDATE = datetime.datetime.strptime(request.values[CT_DATE], "%Y-%m-%d")
            myTIME = request.values[CT_TIME]

            # Infos dans le log
            app.logger.info('')
            app.logger.info(CT_COMPANY + myCOMPANY)
            app.logger.info(CT_DEPARTURE + myDEPARTURE)
            app.logger.info(CT_DATE + myDATE.strftime("%Y-%m-%d"))
            app.logger.info(CT_TIME + myTIME)

            # Nom du modèle en fonction de la compagnie
            model_name = 'model_columns_' + myCOMPANY
            model_df = load_obj(model_name)

            model_cols = load_obj(model_name)
            tbl = [0 for _ in range(len(model_cols.columns))]
            if len(tbl) == 0:
                return model_name + ' not found'
    
            #for col in model_cols:
            #    app.logger.info(col)
    
            # New row
            model_df.loc[0] = 0
            
            # Distance par rapport à un jour férié (en 2016 en tout cas)
            hDay = DaysToHoliday(myDATE)
            app.logger.info('hDay', hDay)
            model_df["HDAYS"] = hDay

            app.logger.info('month', str(myDATE.month))
            model_df["MONTH_" + str(myDATE.month)] = 1

            app.logger.info('weekday', str(myDATE.weekday()))
            model_df["DAY_OF_WEEK_" + str(myDATE.weekday())] = 1

            hh, mm = [int(x) for x in myTIME.split(":")]
            app.logger.info('hh', hh)
            model_df["DEP_HOUR_" + str(hh)] = 1

            # Place de l'aéroport par rapport au modèle de la compagnie
            # Attention toutes les compagnies ne désservent pas tous les aéroports
            col = "ORIGIN_AIRPORT_ID_" + str(myDEPARTURE)
            if col not in model_df.columns:
                return "No departure from " + str(myDEPARTURE) + " for company" + myCOMPANY
            model_df[col] = 1

            scaler = joblib.load(CT_DIR + 'model_scaler_' + myCOMPANY + '.pkl')

            xnum = 1
            x_numerical = model_df.iloc[:, 0:xnum]
            x_numerical = scaler.transform(x_numerical )
            model_df.loc[:, 0:xnum] = x_numerical

            model = joblib.load(CT_DIR + 'model_SGD_' + myCOMPANY + '.pkl')
            y_pred = model.predict(model_df)[0]
            if y_pred > 0:
                result = "<SMALL>Retard :</SMALL>"
            else:
                result = "<SMALL>En avance :</SMALL>"

            min, sec = int(y_pred), int((y_pred%1)*60)
            ret = result + "{:02d}min and {:02d}s".format(min, sec)

            return ret
        except Exception as e:
            return str(e)
    return "NO POST"

