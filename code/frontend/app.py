from flask import Flask, render_template, request, redirect, url_for, flash, session
import firebase_admin
from firebase_admin import credentials, db, auth
from werkzeug.security import generate_password_hash, check_password_hash
import os

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
        activity = request.form['activity']
        day = request.form['day']

        # Reference to the user's bookings
        user_bookings_ref = db.reference(f'users/{user["uid"]}/bookings')
        user_bookings = user_bookings_ref.get() or {}

        # Prevent double booking on the same day and time
        for booking_id, booking in user_bookings.items():
            if booking['day'] == day and booking['time_start'] == request.form['time_start']:
                flash("You already have a booking at this time.", "error")
                return redirect(url_for('offerings'))

        offering_ref = db.reference(f'locations/{offering_id}')
        offering_data = offering_ref.get()

        if offering_data:
            for schedule in offering_data.get('schedule', []):
                if schedule['activity'] == activity and schedule['day'] == day:
                    if user['role'] == 'instructor' and not schedule.get('instructor'):
                        # Instructor booking
                        schedule['instructor'] = user['name']
                        offering_ref.child('schedule').set(offering_data['schedule'])
                        flash("Offering successfully booked for instruction.", "success")
                    elif user['role'] == 'user' and schedule.get('instructor'):
                        # User booking
                        participants = schedule.get('participants', 0)
                        max_participants = schedule.get('max_participants', 0)
                        if participants < max_participants:
                            schedule['participants'] = participants + 1

                            # Mark as full if participants reach max capacity
                            if schedule['participants'] >= max_participants:
                                schedule['is_full'] = True

                            offering_ref.child('schedule').set(offering_data['schedule'])
                            user_bookings_ref.push({
                                'offering_id': offering_id,
                                'location': offering_data['name'],
                                'city': offering_data['city'],
                                'activity': schedule['activity'],
                                'mode': schedule['mode'],
                                'day': schedule['day'],
                                'time_start': schedule['time_start'],
                                'time_end': schedule['time_end'],
                                'instructor': schedule.get('instructor')
                            })
                            flash("Offering successfully booked.", "success")
                        else:
                            flash("This offering is fully booked.", "error")
                    else:
                        flash("You are not authorized to book this offering.", "error")
                    break
            else:
                flash("Offering not found.", "error")
        else:
            flash("Offering not found.", "error")

        return redirect(url_for('offerings'))

    # Fetch and display offerings
    locations_ref = db.reference('locations')
    locations = locations_ref.get() or {}
    offerings_list = []

    for loc_id, loc_data in locations.items():
        for schedule in loc_data.get('schedule', []):
            offering = {
                'location': loc_data['name'],
                'city': loc_data['city'],
                'activity': schedule['activity'],
                'mode': schedule['mode'],
                'day': schedule['day'],
                'time_start': schedule['time_start'],
                'time_end': schedule['time_end'],
                'id': loc_id,
                'instructor': schedule.get('instructor'),
                'is_full': schedule.get('participants', 0) >= schedule.get('max_participants', 0)
            }
            offerings_list.append(offering)

    return render_template('offerings.html', offerings=offerings_list, user=user)



@app.route('/instructor/bookings')
def instructor_bookings():
    user = session.get('user')
    if not user or user['role'] != 'instructor':
        flash("Access denied. Only instructors can view their bookings.", "error")
        return redirect(url_for('index'))

    # Fetch all locations
    locations_ref = db.reference('locations')
    locations = locations_ref.get() or {}
    instructor_bookings_list = []

    # Iterate through locations and their schedules
    for loc_id, loc_data in locations.items():
        for schedule in loc_data.get('schedule', []):
            if schedule.get('booked_by') == user['name']:
                instructor_bookings_list.append({
                    'location': loc_data['name'],
                    'city': loc_data['city'],
                    'activity': schedule['activity'],
                    'mode': schedule['mode'],
                    'day': schedule['day'],
                    'time_start': schedule['time_start'],
                    'time_end': schedule['time_end'],
                    'id': loc_id
                })

    return render_template('instructor_bookings.html', bookings=instructor_bookings_list, user=user)


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

@app.route('/admin/all_bookings')
def all_bookings():
    user = session.get('user')
    if not user or user['role'] != 'admin':
        flash("Access denied. Only admins can view all bookings.", "error")
        return redirect(url_for('index'))

    # Reference to all users
    users_ref = db.reference('users')
    users = users_ref.get() or {}

    all_bookings_list = []

    for uid, user_data in users.items():
        bookings_ref = db.reference(f'users/{uid}/bookings')
        bookings = bookings_ref.get() or {}
        for booking_id, booking_data in bookings.items():
            booking_data['client_name'] = user_data.get('name', 'Unknown')
            booking_data['client_email'] = user_data.get('email', 'Unknown')
            all_bookings_list.append(booking_data)

    return render_template('all_bookings.html', bookings=all_bookings_list, user=user)

@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    user = session.get('user')
    if not user or user['role'] != 'admin':
        flash("Access denied. Only admins can manage user accounts.", "error")
        return redirect(url_for('index'))

    users_ref = db.reference('users')
    users = users_ref.get() or {}

    if request.method == 'POST':
        user_id_to_delete = request.form.get('user_id')
        if user_id_to_delete:
            # Prevent admin from deleting their own account
            if user_id_to_delete == user['uid']:
                flash("You cannot delete your own account.", "error")
                return redirect(url_for('admin_users'))

            # Attempt to delete user from Firebase Authentication
            try:
                auth.delete_user(user_id_to_delete)
                flash("User deleted from authentication.", "success")
            except firebase_admin.auth.UserNotFoundError:
                # User not found in authentication; proceed without flashing an error
                pass
            except Exception as e:
                flash(f"Done")

            # Delete user data from Realtime Database
            user_ref = users_ref.child(user_id_to_delete)
            if user_ref.get():
                user_ref.delete()
                flash("User data deleted successfully.", "success")
            else:
                flash("User data not found.", "error")

            return redirect(url_for('admin_users'))

    return render_template('admin_users.html', users=users, user=user)


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
        role = request.form['role']
        age = int(request.form.get('age', 18))  # Default to 18 if not provided

        # Optional: Capture guardian details for users under 18
        guardian_name = request.form.get('guardian_name') if age < 18 else None
        guardian_relation = request.form.get('guardian_relation') if age < 18 else None

        # Handle city selection for instructors
        cities = request.form.getlist('cities') if role == 'instructor' else []

        # Check if an account with the same email already exists
        user_ref = db.reference('users').order_by_child('email').equal_to(email).get()
        if user_ref:
            flash("An account with this email already exists.", "error")
            return redirect(url_for('register'))

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Push the new user data to the database
        new_user_ref = db.reference('users').push({
            'name': name,
            'email': email,
            'password': hashed_password,
            'role': role,
            'age': age,
            'guardian_name': guardian_name,
            'guardian_relation': guardian_relation,
            'cities': cities  # Save selected cities for instructors
        })

        # Store user session data
        session['user'] = {
            'uid': new_user_ref.key,
            'name': name,
            'role': role
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
                    'booked_by': None,
                    'is_booked': False
                }
            ]
        }

        # Save the offering to Firebase
        db.reference('locations').push(offering_data)

        flash("New offering created successfully!", "success")
        return redirect(url_for('offerings'))

    return render_template('new_offering.html')



@app.route('/delete_account/<user_id>', methods=['POST'])
def delete_account(user_id):
    current_user = session.get('user')
    if not current_user:
        flash("Please log in to delete an account.", "error")
        return redirect(url_for('login'))

    # Check if the current user is trying to delete their own account
    if current_user['uid'] == user_id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('admin_dashboard'))  # Redirect to an appropriate page

    # Proceed with deletion for other users
    user_ref = db.reference(f'users/{user_id}')
    if user_ref.get():
        user_ref.delete()
        flash("Account deleted successfully.", "success")
    else:
        flash("Account not found.", "error")

    return redirect(url_for('admin_dashboard'))  # Redirect to an appropriate page

@app.route('/instructor/book_offering', methods=['POST'])
def book_offering():
    user = session.get('user')
    if not user or user['role'] != 'instructor':
        flash("Access denied. Only instructors can book offerings.", "error")
        return redirect(url_for('index'))

    offering_id = request.form['offering_id']
    offering_ref = db.reference(f'locations/{offering_id}')
    offering_data = offering_ref.get()

    if offering_data:
        # Check if the offering is already booked
        if offering_data['schedule'][0].get('is_booked'):
            flash("This offering has already been booked by another instructor.", "error")
        else:
            # Update the offering's booking status
            offering_ref.child('schedule/0').update({
                'is_booked': True,
                'booked_by': user['name']
            })
            flash("Offering successfully booked.", "success")
    else:
        flash("Offering not found.", "error")

    return redirect(url_for('available_offerings'))




@app.route('/instructor/available_offerings')
def available_offerings():
    user = session.get('user')
    if not user or user['role'] != 'instructor':
        flash("Access denied. Only instructors can view available offerings.", "error")
        return redirect(url_for('index'))

    # Fetch offerings that are not yet booked
    locations_ref = db.reference('locations')
    locations = locations_ref.get() or {}
    available_offerings = []
    for loc_id, loc_data in locations.items():
        for schedule in loc_data.get('schedule', []):
            if not schedule.get('is_booked'):
                available_offerings.append({
                    'location': loc_data['name'],
                    'city': loc_data['city'],
                    'activity': schedule['activity'],
                    'mode': schedule['mode'],
                    'day': schedule['day'],
                    'time_start': schedule['time_start'],
                    'time_end': schedule['time_end'],
                    'id': loc_id
                })

    return render_template('available_offerings.html', offerings=available_offerings, user=user)


if __name__ == '__main__':
    app.run(debug=True)