from geopy.geocoders import Nominatim
import smtplib
from geopy.distance import great_circle
from flask import Flask, render_template, request, redirect, url_for
import pymongo
import folium
from folium import Figure

app = Flask(__name__)
client = pymongo.MongoClient(
    "mongodb+srv://admin:admin@cluster0.lifk8.mongodb.net/test")
db = client.get_database('Carpool')
data = db['Clients']
user_id = ''
geolocator = Nominatim(user_agent="Carpool")
user_Query = False


def checkUser(username, userEmail):
    if(data.find_one({'_id': username, 'email': userEmail})):
        return True
    else:
        return False


def checkLoc(x, y):
    userloc = geolocator.geocode(x)
    ownerloc = geolocator.geocode(y)
    if(bool(userloc) and bool(ownerloc)):
        return int(great_circle((userloc.latitude, userloc.longitude), (ownerloc.latitude, ownerloc.longitude)).km)
    else:
        return False


def genMap(userFrom, ownerFrom):

    values = {}
    values['distanceBtw'] = checkLoc(userFrom, ownerFrom)
    values['timeTaken'] = values['distanceBtw']/40

    user = geolocator.geocode(userFrom)
    owner = geolocator.geocode(ownerFrom)
    uLat = user.latitude
    uLong = user.longitude

    oLat = owner.latitude
    oLong = owner.longitude

    fig = Figure(width=550, height=350)
    map = folium.Map(location=[uLat, uLong], zoom_start=10)
    fig.add_child(map)

    folium.Marker(location=[uLat, uLong], popup=userFrom,
                  tooltip='Your location').add_to(map)
    folium.Marker(location=[oLat, oLong], popup=ownerFrom,
                  tooltip='Fellow traveler location').add_to(map)

    map.save("templates/mainMap.html")

    return values


@app.route('/details')
def details():
    sendMail()
    connectData = data.find_one({'_id': request.args.get('connectId')})
    userData = data.find_one({'_id': user_id})
    # ownerData = data.find_one({'_id': connectId})

    imp_val = genMap(userData['from_loc'], connectData['from_loc'])

    return render_template('details.html', ownerData=connectData, travelVal=imp_val)


@app.route('/big-map')
def bigMap():
    return render_template('mainMap.html')


@app.route('/send_mail')
def sendMail():

    connectData = data.find({'_id': request.args.get('connectId')})
    global user_id
    userData = data.find_one({'_id': user_id})
    connectData = connectData.next()
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login("testmailcarpool@gmail.com", "carpoolTestMail")
    connectMsg = '''Subject: Details Requested Alert | Carpool\n\n
Greetings from Carpool,\n
The below mentioned person has viewed your details.
Name : {}
Phone : {}
Email : {}
Gender : {}
Age : {}
Destination : {}
\nKindly please contact them for further clarification
Thanks & Regards
Team Carpool'''.format(userData['name'], userData['mobile'], userData['email'], userData['gender'], userData['age'], userData['to_loc'])
    server.sendmail("testmailcarpool@gmail.com",
                    connectData['email'], connectMsg)
    server.quit()


@app.route('/login/', methods=['GET', 'POST'])
def login():

    global user_id
    user_id = ''
    if(request.method == 'POST'):
        user_id = request.form.get('username')
        user_data = data.find_one({'_id': user_id})

        if(user_data):
            if(user_data['password'] == request.form.get('password')):
                return redirect(url_for("home"))
            else:
                error = "Incorrect Password"
                return render_template('login.html', login_error=error)
        else:
            return render_template('login.html', login_error="Incorrect Username")
    return render_template('login.html')


@app.route('/', methods=['GET', 'POST'])
def home():
    global user_id
    if(request.method == 'POST'):
        if(user_id != ''):
            srchLoc = geolocator.geocode(request.form.get('search'))
            if(bool(srchLoc)):
                user_Query = True
                result = data.find(
                    {"to_loc": request.form.get('search').lower()})
                return render_template('index1.html', searchQuery=user_Query, record=result, userID=user_id)
            return render_template('index1.html', location_error="Try another Destination")
        return render_template('login.html', login_error="Please login first")
    return render_template('index1.html', userID=user_id)


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if(request.method == 'POST'):

        global user_id
        user_id = request.form.get('username')
        user_password = request.form.get('password')
        user_email = request.form.get('email')
        # user_already_data = data.find_one({'_id': user_id})


        if (not checkUser(user_id, user_email)):
            if(checkLoc(request.form.get('from'), request.form.get('to'))):
                data.insert_one({
                    '_id': user_id,
                    'name': request.form.get('name'),
                    'type': request.form.get('user_type'),
                    'gender': request.form.get('gender'),
                    'age': int(request.form.get('age')),
                    'email': user_email,
                    'mobile': int(request.form.get('phone')),
                    'from_loc': request.form.get('from').lower(),
                    'to_loc': request.form.get('to').lower(),
                    'password': user_password,
                })
                return redirect(url_for("home"))
            return render_template("register.html", location_error="Try other Location")
        return render_template("login.html", register_error="User Already Exist")
    return render_template('register.html', user_data = "" )

@app.route('/modify/', methods=['GET', 'POST'])
def modify():
    global user_id
    if(request.method == 'POST'):
        user_data = data.find_one({'_id': user_id})
        # user_password = request.form.get('password')
        # user_email = request.form.get('email')
        if(user_data):
            if(checkLoc(request.form.get('from'), request.form.get('to'))):
                data.update_one({'type': user_data['type'],
                                        'age': user_data['age'],
                                        'email': user_data['email'],
                                        'mobile': user_data['mobile'],
                                        'from_loc': user_data['from_loc'],
                                        'to_loc': user_data['to_loc'],
                                        'password': user_data['password']
                                        },
                                {"$set":{
                                'type': request.form.get('user_type'),
                                'age': int(request.form.get('age')),
                                'email': request.form.get('email'),
                                'mobile': int(request.form.get('phone')),
                                'from_loc': request.form.get('from').lower(),
                                'to_loc': request.form.get('to').lower(),
                                'password': request.form.get('password'),                                    
                                }})
                return redirect(url_for("home"))
            return render_template("modify.html", location_error = "Try another location")
    return render_template('modify.html')


if __name__ == "__main__":
    app.run(debug=True)
