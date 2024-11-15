from flask import Flask, render_template, request, redirect, url_for, flash, session
import firebase_admin
from firebase_admin import credentials, db
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize Firebase
cred = credentials.Certificate("credentials.json")
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