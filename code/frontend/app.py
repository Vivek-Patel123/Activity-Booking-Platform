from flask import Flask, render_template, request, redirect, url_for, flash, session
import firebase_admin
from firebase_admin import credentials, db
from werkzeug.security import generate_password_hash, check_password_hash

# Firebase credentials embedded directly in the code
firebase_credentials = {
    "type": "service_account",
    "project_id": "soen342-929fb",
    "private_key_id": "a10bc1dd5df9b0355ed41d2c38249988042bfdc2",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCYCXaNAbenpVsR\n27qIgSZowUMPGRGu56BFISMTb4tEAhM2ac4jMCqIrvqLxxqMaHfJ0NV23rPO31kX\nUag12gqskFTvKLBJG7tka5b51tp50fWwUt6fwcGQR3rIrJMy12A56gLxnUeQ/xQh\ngS5MMutZnlDRzDZHqYcca+exyHf3m1v44fubjiZmu8b9TeEtCv471EWvZc2MCLCy\nnsbQF1ICZ0v99JAmIqbqD6Il+uRSPQtVLDbi94CZTWGCJeqcg0bweMDc1irZ/sXX\no3RPqnN0FZuyCiOpIdDi6U8IIrG+hM8jnC8hKT55bN21GAqNBm0xOBIm4BhP6Rg1\nzWmBnX3/AgMBAAECggEABv2hi0iPgP4tKGVXgPNRljuBQ9wrhNcJG0APGRzTm+02\nyPDeOnmxWvuTA15W5L1OsCykDTwMPacu2c/tY9Nd7kejiUg5Yt6dkcntPmKF13yz\nIn76sZL64hF1DCSOs5N58YIPqSmTEJAA4Kzwy8C6fHuSzFdYVnPIzuu/QG7l5UKq\nM+PLNANEFmvNLjMpByESzwX3/K4fz9JV27NUJtkEnjLMiY2m6YZx30XBAwqrbK5Z\ngmJlTQy3bH+qzjMe7EKGX8i1arr5mWvaxOAvgn/rI3ECSrV3tpAd8hSgdKaViW8Z\nq/B2Qgws4tUwpLdAvkkhiLpSOLW1eTppuEdemit3EQKBgQDOBEtCfS9v0EaB53fB\nAA8BM7OLDrJkN37P1h8lqPUqZmqYjWL+hO/QfeXlXl5iM3UXmE55q+mFEzbzO+NS\nehCjKdiHwFJ+2YkJ0woWHONURyqL2wCm0jMTbNJpoKrOxwKLppms7537RR8gPtW+\nGIBvBUjpMojUVrHwLL9io6LhowKBgQC87Htrx3vbEkGajEfVj/VLZhe8OR8XE3O4\nflF547oYoIbq8eAZSOCz6DO2pOFm6ufzezGBW64XSP+mTmXKdILGiCdwbVUES4gw\ngvPShp1IZUpOBnxO8CREDwd2P/Y1P5eNuMf4pcu5J6a+Gdz1jQyS5mgHObeP/NFA\n532g/KEP9QKBgFytXdXZTv+z6CQEJsEx744Q3hIOWH3w4SFKJ9TfPvsF+6oI4KGy\n19co68TVQQxYLbKhl5vwlCqDTFL7e/XcZ6Oe7YOUJwhdf+Jlh8IO2M1O/nrP2Gkz\nYjq416cg2fYPXLvKBJPhb2Zb3/a3jZvolc5byELvstIi9gUffDE5f8qVAoGALhGI\ngx6w0Bnij3o3phclnI43qXlQYIMoy8tZuNxUK98xJyd2GxRPXu93dMk+Aae0igX3\na3DcwebWGEqzvautnBXlcB/pBFQa0KGOLT8QKXAxr1cbhvA+F66GhkpQkmmAXlm5\nwaNES1Ek8uRBoksTztqKcYCch2sB587LLq+L4uUCgYEAkWTcKfIrnGn4jgieHL+l\nKLRHt5HMEqRD2MaKV9SYl484HxytrI4BPCNBYJWh76/FBZAAK7dAdX4gtgVkad+h\nmRU57Kg0u7F7oPjUar+KxN1O2JRIZgnztpMtszFJ6kTLdPatyIfpvF8qdep2vCWu\nmi0v5gKyzGWLah6u5KxYn4A=\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-ubput@soen342-929fb.iam.gserviceaccount.com",
    "client_id": "111412042221283001147"
}

# Initialize Firebase using the embedded credentials
cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://soen342-929fb-default-rtdb.firebaseio.com"
})

app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def index():
    user = session.get('user')
    return render_template('index.html', user=user)


@app.route('/offerings', methods=['GET', 'POST'])
def offerings():
    user = session.get('user')

    if request.method == 'POST':
        if not user:
            flash("Please log in to book an offering.", "error")
            return redirect(url_for('login'))

        offering_id = request.form['offering_id']
        instructor_name = user['name']
        
        # Reference to the specific offering
        offering_ref = db.reference(f'locations/{offering_id}')
        offering_data = offering_ref.get()

        if offering_data:
            # Retrieve the user's existing bookings
            user_bookings_ref = db.reference(f'users/{user["uid"]}/bookings')
            existing_bookings = user_bookings_ref.get() or {}

            # Check if the user has already booked this offering
            for booking in existing_bookings.values():
                if booking['location'] == offering_data['name'] and booking['activity'] == offering_data['schedule'][0]['activity']:
                    flash("You have already booked this offering.", "error")
                    return redirect(url_for('offerings'))

            # Proceed with booking
            for schedule in offering_data['schedule']:
                if schedule.get('mode') == 'private' and not schedule.get('booked_by'):
                    schedule['booked_by'] = instructor_name
                    flash(f"Offering successfully booked by {instructor_name}.", "success")
                elif schedule.get('mode') == 'group':
                    participants = schedule.get('participants', 0)
                    max_participants = schedule.get('max_participants', 0)
                    if participants < max_participants:
                        schedule['participants'] = participants + 1
                        flash(f"Offering successfully booked by {instructor_name}.", "success")
                    else:
                        flash("This group offering is fully booked.", "error")
                else:
                    flash("This private offering is already booked.", "error")

            # Update the Firebase entry
            offering_ref.child('schedule').set(offering_data['schedule'])

            # Add the booking to the user's bookings
            user_bookings_ref.push({
                'location': offering_data['name'],
                'city': offering_data['city'],
                'activity': offering_data['schedule'][0]['activity'],
                'mode': offering_data['schedule'][0]['mode'],
                'day': offering_data['schedule'][0]['day'],
                'time_start': offering_data['schedule'][0]['time_start'],
                'time_end': offering_data['schedule'][0]['time_end']
            })
            return redirect(url_for('my_bookings'))

    # Fetch and display available offerings
    locations_ref = db.reference('locations')
    locations = locations_ref.get() or {}
    offerings_list = []
    for loc_id, loc_data in locations.items():
        for schedule in loc_data.get('schedule', []):
            offerings_list.append({
                'location': loc_data['name'],
                'city': loc_data['city'],
                'activity': schedule['activity'],
                'mode': schedule['mode'],
                'day': schedule['day'],
                'time_start': schedule['time_start'],
                'time_end': schedule['time_end'],
                'id': loc_id
            })

    return render_template('offerings.html', offerings=offerings_list, user=user)


@app.route('/my_bookings')
def my_bookings():
    user = session.get('user')
    if not user:
        flash("Please log in to view your bookings.", "error")
        return redirect(url_for('login'))

    user_bookings_ref = db.reference(f'users/{user["uid"]}/bookings')
    bookings = user_bookings_ref.get() or {}

    return render_template('my_bookings.html', bookings=bookings, user=user)


@app.route('/delete_booking/<booking_id>', methods=['POST'])
def delete_booking(booking_id):
    user = session.get('user')
    if not user:
        flash("Please log in to delete a booking.", "error")
        return redirect(url_for('login'))

    user_bookings_ref = db.reference(f'users/{user["uid"]}/bookings')
    booking_ref = user_bookings_ref.child(booking_id)
    if booking_ref.get():
        booking_ref.delete()
        flash("Booking deleted successfully.", "success")
    else:
        flash("Booking not found.", "error")

    return redirect(url_for('my_bookings'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_ref = db.reference('users').order_by_child('email').equal_to(email).get()
        user_data = next(iter(user_ref.values()), None)
        if user_data and check_password_hash(user_data['password'], password):
            session['user'] = {
                'uid': next(iter(user_ref.keys())),
                'name': user_data.get('name'),
                'role': user_data.get('role')
            }
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "error")
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        user_ref = db.reference('users').order_by_child('email').equal_to(email).get()
        if user_ref:
            flash("An account with this email already exists.", "error")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user_ref = db.reference('users').push({
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': 'user'
        })
        session['user'] = {
            'uid': new_user_ref.key,
            'name': name,
            'role': 'user'
        }
        flash("Registration successful! You are now logged in.", "success")
        return redirect(url_for('index'))
    return render_template('register.html')

@app.context_processor
def inject_user():
    return {'user': session.get('user')}

@app.route('/admin/new-offering', methods=['GET', 'POST'])
def new_offering():
    user = session.get('user')
    if not user or user['role'] != 'admin':
        flash("Access denied. Only admins can create offerings.", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        city = request.form.get('city')
        time_start = request.form.get('time_start')
        time_end = request.form.get('time_end')
        lesson_type = request.form.get('lesson_type')
        max_participants = int(request.form.get('max_participants')) if lesson_type == 'group' else None
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        # Validate required fields
        if not all([title, location, city, time_start, time_end, lesson_type, start_date, end_date]):
            flash("All fields are required.", "error")
            return redirect(url_for('new_offering'))

        # Create a new offering object
        offering_data = {
            'name': title,
            'city': city,
            'schedule': [
                {
                    'activity': title,
                    'mode': lesson_type,
                    'time_start': time_start,
                    'time_end': time_end,
                    'day': "All Days",
                    'start_date': start_date,
                    'end_date': end_date,
                    'participants': 0 if lesson_type == 'group' else None,
                    'max_participants': max_participants,
                    'booked_by': None
                }
            ]
        }

        # Save the offering to Firebase
        db.reference('locations').push(offering_data)

        flash("New offering created successfully!", "success")
        return redirect(url_for('offerings'))

    return render_template('new_offering.html')

if __name__ == '__main__':
    app.run(debug=True)
