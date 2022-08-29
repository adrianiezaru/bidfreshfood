from cs50 import SQL
from flask_session import Session
from flask import Flask, render_template, redirect, request, session, abort
from datetime import datetime
import base64
import hashlib
import secrets
from werkzeug.utils import secure_filename
import os
import imghdr

# instantiate Flask object named app
app = Flask(__name__)

# configure sessions
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

app.config["UPLOAD_EXTENSIONS"] = [".jpg", ".png"]  # image upload extensions
app.config["UPLOAD_PATH"] = "static/img/"  # image upload directory
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 10  # max image size

Session(app)

# creates a connection to the database
db = SQL("sqlite:///db.sqlite3")


# encode password to pbkdf2_sha256
def hash_password(password, salt=None, iterations=320000):
    if salt is None:
        salt = secrets.token_hex(16)
    assert salt and isinstance(salt, str) and "$" not in salt
    assert isinstance(password, str)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    b64_hash = base64.b64encode(pw_hash).decode("ascii").strip()
    return "{}${}${}${}".format("pbkdf2_sha256", iterations, salt, b64_hash)


# verify pbkdf2_sha256 password if it matches
def verify_password(password, password_hash):
    if (password_hash or "").count("$") != 3:
        return False
    algorithm, iterations, salt, b64_hash = password_hash.split("$", 3)
    iterations = int(iterations)
    assert algorithm == "pbkdf2_sha256"
    compare_hash = hash_password(password, salt, iterations)
    return secrets.compare_digest(password_hash, compare_hash)


# check if the uploaded file is really an image
def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return "." + (format if format != "jpeg" else "jpg")


# homepage
@app.route("/")
def index():

    # list all bids available
    auctions = db.execute("SELECT * FROM auctions_listing")

    # Initialize variables
    activeBids = {}
    bidsSum = 0
    bidMoney = {}

    # check if logged
    if "user" in session:
        # render watchlist
        watchList = db.execute(
            "SELECT * FROM auctions_listing_watchListUsers where user_id = :user_id",
            user_id=session["uid"],
        )
        watchListLen = len(watchList)

        # render active bids
        listings = db.execute(
            "SELECT id, listing_id, value FROM auctions_bid WHERE user_id = :userid",
            userid=session["uid"],
        )
        for listing in listings:
            activeBids[listing["listing_id"]] = [listing["value"], listing["id"]]
            bidMoney[listing["listing_id"]] = listing["value"]
        for bid in bidMoney:
            bidsSum += bidMoney[bid]
        bidsLen = len(bidMoney)

        return render_template(
            "index.html",
            activeBids=activeBids,
            auctions=auctions,
            bidsLen=bidsLen,
            bidsSum=bidsSum,
            session=session,
            watchList=watchList,
            watchListLen=watchListLen,
        )

    return render_template("index.html", auctions=auctions, activeBids=activeBids)


# view active bids
def viewbids():
    # select all auctions
    auctions = db.execute("SELECT * FROM auctions_listing")
    auctionsLen = len(auctions)

    watchList = db.execute(
        "SELECT * FROM auctions_listing_watchListUsers where user_id = :user_id",
        user_id=session["uid"],
    )
    watchListLen = len(watchList)

    # initialize variables
    activeBids = {}
    bidsSum = 0
    bidMoney = {}

    # select bids from database
    listings = db.execute(
        "SELECT id, listing_id, value FROM auctions_bid WHERE user_id = :userid",
        userid=session["uid"],
    )
    # store for latest bid value and bid id for every item
    for listing in listings:
        activeBids[listing["listing_id"]] = [listing["value"], listing["id"]]
        bidMoney[listing["listing_id"]] = listing["value"]

    # store total bid
    for bid in bidMoney:
        bidsSum += bidMoney[bid]

    # store number of bids
    bidsLen = len(bidMoney)
    return render_template(
        "cart.html",
        activeBids=activeBids,
        auctions=auctions,
        bidsLen=bidsLen,
        bidsSum=bidsSum,
        session=session,
        watchList=watchList,
        watchListLen=watchListLen,
    )


@app.route("/placebid/")
def buy():
    if session:
        # get the bid id
        listing_id = int(request.args.get("listingId"))

        # get the bid value
        sendBid = int(request.args.get("sendBid"))

        # select bid by id from database
        items = db.execute(
            "SELECT * FROM auctions_listing WHERE id = :id", id=listing_id
        )

        # get current bid value
        currentBid = items[0]["currentBidValue"]

        # get current timestamp
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

        # insert bid into database
        db.execute(
            "INSERT INTO auctions_bid (datetime, value, listing_id, user_id)  VALUES (:datetime, :value, :listing_id, :user_id)",
            datetime=ts,
            value=sendBid,
            listing_id=listing_id,
            user_id=session["uid"],
        )

        # update highest bid
        if sendBid > currentBid:
            db.execute(
                "UPDATE auctions_listing  SET currentBidValue = :highestBid WHERE id = :listing_id",
                highestBid=sendBid,
                listing_id=listing_id,
            )

        # view all bids for current user
        return viewbids()

    else:
        # unauthorized to place bid when not logged in
        abort(401)


@app.route("/close-auction/")
def closeAuction():
    if session:

        # store id of the selected closing item
        close_listing_id = int(request.args.get("clistingId"))

        # select winner user id
        winner = db.execute(
            "SELECT MAX(value) as winnerbid, user_id FROM auctions_bid WHERE listing_id = :close_listing_id",
            close_listing_id=close_listing_id,
        )

        # delete all bids for closed auction
        db.execute(
            "DELETE FROM auctions_bid WHERE listing_id = :close_listing_id",
            close_listing_id=close_listing_id,
        )

        # finding winner id
        winner_id = winner[0]["user_id"]

        # if no bids, then author is the winner
        if winner_id is None:
            winner_id = session["uid"]

        # close auction
        db.execute(
            "UPDATE auctions_listing  SET isOpen = 0, winner_id = :winner_uid WHERE id = :close_listing_id and user_id = :currentUser",
            winner_uid=winner_id,
            currentUser=session["uid"],
            close_listing_id=close_listing_id,
        )

        return myItems()
    else:
        abort(401)


@app.route("/watch/")
def watch():
    if session:
        # get id of item
        listing_id = int(request.args.get("listingId"))

        # watch item
        try:
            db.execute(
                "INSERT INTO auctions_listing_watchListUsers (listing_id, user_id)  VALUES (:listing_id, :user_id)",
                listing_id=listing_id,
                user_id=session["uid"],
            )
        except ValueError:
            pass
        return index()
    else:
        abort(401)


@app.route("/my-items/")
def myItems():
    if session:
        # select all auctions
        auctions = db.execute(
            "SELECT * FROM auctions_listing where user_id = :user_id",
            user_id=session["uid"],
        )
        auctionsLen = len(auctions)

        # select all users
        users = db.execute("SELECT id,first_name,last_name FROM auctions_user")
        userlist = {}

        # store for every user id the full name
        for user in users:
            userlist[user["id"]] = [user["first_name"], user["last_name"]]

        # get the watchlist for the user
        watchList = db.execute(
            "SELECT * FROM auctions_listing_watchListUsers where user_id = :user_id",
            user_id=session["uid"],
        )
        watchListLen = len(watchList)

        # initialize variables
        activeBids = {}
        bidsSum = 0
        user_bids_sum = 0
        bidMoney = {}

        # get active bids for user id
        listings = db.execute(
            "SELECT id, listing_id, value FROM auctions_bid WHERE user_id = :userid",
            userid=session["uid"],
        )

        # store for latest bid value and bid id for every item
        for listing in listings:
            activeBids[listing["listing_id"]] = [listing["value"], listing["id"]]
            bidMoney[listing["listing_id"]] = listing["value"]
        for bid in bidMoney:
            bidsSum += bidMoney[bid]

        # store total bid
        for auction in auctions:
            user_bids_sum += auction["currentBidValue"]

        bidsLen = len(bidMoney)
        mybidsLen = len(auctions)

        return render_template(
            "my-items.html",
            activeBids=activeBids,
            auctions=auctions,
            mybidsLen=mybidsLen,
            user_bids_sum=user_bids_sum,
            session=session,
            userlist=userlist,
            watchList=watchList,
            watchListLen=watchListLen,
            bidsSum=bidsSum,
            bidsLen=bidsLen,
        )
    else:
        abort(401)


@app.route("/my-won-bids/")
def myWon():
    if session:
        # select the items wheren winner id is the user id
        won_auctions = db.execute(
            "SELECT * FROM auctions_listing where isOpen == 0 and winner_id = :user_id",
            user_id=session["uid"],
        )
        auctionsLen = len(won_auctions)

        auctions = db.execute("SELECT * FROM auctions_listing")

        # select all users
        users = db.execute("SELECT id,first_name,last_name FROM auctions_user")
        userlist = {}

        # store for every user id the full name
        for user in users:
            userlist[user["id"]] = [user["first_name"], user["last_name"]]

        # get the watchlist for the user
        watchList = db.execute(
            "SELECT * FROM auctions_listing_watchListUsers where user_id = :user_id",
            user_id=session["uid"],
        )
        watchListLen = len(watchList)

        # initialize variables
        activeBids = {}
        bidsSum = 0
        user_bids_sum = 0
        bidMoney = {}

        # get active bids for user id
        listings = db.execute(
            "SELECT id, listing_id, value FROM auctions_bid WHERE user_id = :userid",
            userid=session["uid"],
        )

        # store latest bid value and bid id for every item
        for listing in listings:
            activeBids[listing["listing_id"]] = [listing["value"], listing["id"]]
            bidMoney[listing["listing_id"]] = listing["value"]
        for bid in bidMoney:
            bidsSum += bidMoney[bid]

        # store total for won bids
        for auction in won_auctions:
            user_bids_sum += auction["currentBidValue"]

        # store active bids
        bidsLen = len(bidMoney)

        # store won bids
        won_bids = len(won_auctions)

        return render_template(
            "my-won-bids.html",
            activeBids=activeBids,
            auctions=auctions,
            auctionsLen=auctionsLen,
            won_auctions=won_auctions,
            won_bids=won_bids,
            user_bids_sum=user_bids_sum,
            session=session,
            userlist=userlist,
            watchList=watchList,
            watchListLen=watchListLen,
            bidsSum=bidsSum,
            bidsLen=bidsLen,
        )
    else:
        abort(401)


@app.route("/add-comment/")
def sendcomment():
    if session:
        # get comment
        comment = request.args.get("message")
        listing_id = int(request.args.get("item_id"))

        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

        if len(comment) < 1:
            return selectItem()

        db.execute(
            "INSERT INTO auctions_comment (datetime, content, listing_id, user_id)  VALUES (:ts, :comment, :listing_id, :user_id)",
            ts=ts,
            comment=comment,
            listing_id=listing_id,
            user_id=session["uid"],
        )

        return selectItem()
    else:
        abort(401)


@app.route("/view-bid/")
def selectItem():

    # get item-id
    item_id = int(request.args.get("item_id"))

    # get item from database
    item = db.execute(
        "SELECT * FROM auctions_listing where id = :item_id", item_id=item_id
    )

    comments = db.execute(
        "SELECT * FROM auctions_comment where listing_id = :item_id", item_id=item_id
    )
    commentsLen = len(comments)

    # get users from database
    users = db.execute("SELECT id,first_name,last_name FROM auctions_user")
    userlist = {}

    # store for every user id the full name
    for user in users:
        userlist[user["id"]] = [user["first_name"], user["last_name"]]

    if session:

        # get all auctions
        auctions = db.execute("SELECT * FROM auctions_listing")

        # get watchlist for userid
        watchList = db.execute(
            "SELECT * FROM auctions_listing_watchListUsers where user_id = :user_id",
            user_id=session["uid"],
        )
        watchListLen = len(watchList)

        # initialize variables
        activeBids = {}
        bidsSum = 0
        user_bids_sum = 0
        bidMoney = {}

        # get all active bids
        listings = db.execute(
            "SELECT id, listing_id, value FROM auctions_bid WHERE user_id = :userid",
            userid=session["uid"],
        )
        for listing in listings:
            activeBids[listing["listing_id"]] = [listing["value"], listing["id"]]
            bidMoney[listing["listing_id"]] = listing["value"]
        for bid in bidMoney:
            bidsSum += bidMoney[bid]
        # get number of active bids
        bidsLen = len(bidMoney)

        return render_template(
            "view-bid.html",
            activeBids=activeBids,
            user_bids_sum=user_bids_sum,
            session=session,
            userlist=userlist,
            watchList=watchList,
            watchListLen=watchListLen,
            bidsSum=bidsSum,
            items=item,
            bidsLen=bidsLen,
            auctions=auctions,
            comments=comments,
            commentsLen=commentsLen,
        )
    else:
        return render_template(
            "view-bid.html",
            items=item,
            comments=comments,
            commentsLen=commentsLen,
            userlist=userlist,
        )


@app.route("/remove/", methods=["GET"])
def remove():
    if session:
        # get the remove bid id
        listing_id = int(request.args.get("rListingId"))
        # remove bid
        db.execute(
            "DELETE from auctions_bid WHERE listing_id = :listing_id AND user_id = :user_id",
            listing_id=listing_id,
            user_id=session["uid"],
        )
        # view all current bids
        return viewbids()
    else:
        abort(401)


@app.route("/delete-auction/")
def deleteAuction():
    if session:
        # get the listing id to be removed
        listing_id = int(request.args.get("clistingId"))

        # remove Item from Tables with Foreign Key listing_id
        db.execute("DELETE from auctions_bid WHERE listing_id = :id", id=listing_id)
        db.execute("DELETE from auctions_comment WHERE listing_id = :id", id=listing_id)
        db.execute(
            "DELETE from auctions_listing_losers WHERE listing_id = :id", id=listing_id
        )
        db.execute(
            "DELETE from auctions_listing_watchListUsers WHERE listing_id = :id",
            id=listing_id,
        )

        # remove listing image
        result = db.execute(
            "SELECT imageURL from auctions_listing WHERE id = :id AND user_id = :uid",
            id=listing_id,
            uid=session["uid"],
        )
        os.remove(app.root_path + result[0]["imageURL"])

        # remove listing
        db.execute(
            "DELETE from auctions_listing WHERE id = :id AND user_id = :uid",
            id=listing_id,
            uid=session["uid"],
        )

        # render updated my items
        return myItems()

    else:
        abort(401)


@app.route("/stopwatching/", methods=["GET"])
def stopwatching():
    if session:
        # get the id of the item
        listing_id = int(request.args.get("rListingId"))

        # remove the id from the watchlist for the user
        db.execute(
            "DELETE from auctions_listing_watchListUsers WHERE listing_id = :listing_id AND user_id = :user_id",
            listing_id=listing_id,
            user_id=session["uid"],
        )

        # get all auctions from database
        auctions = db.execute("SELECT * FROM auctions_listing")
        auctionsLen = len(auctions)

        # get the watchlist
        watchList = db.execute(
            "SELECT * FROM auctions_listing_watchListUsers where user_id = :user_id",
            user_id=session["uid"],
        )
        watchListLen = len(watchList)

        # initialize variables
        activeBids = {}
        bidsSum = 0
        bidMoney = {}
        listings = db.execute(
            "SELECT id, listing_id, value FROM auctions_bid WHERE user_id = :userid",
            userid=session["uid"],
        )
        # get all active bids
        for listing in listings:
            activeBids[listing["listing_id"]] = [listing["value"], listing["id"]]
            bidMoney[listing["listing_id"]] = listing["value"]
        for bid in bidMoney:
            bidsSum += bidMoney[bid]

        # get number of active bids
        bidsLen = len(bidMoney)
        return render_template(
            "watch.html",
            activeBids=activeBids,
            auctions=auctions,
            bidsLen=bidsLen,
            bidsSum=bidsSum,
            session=session,
            watchList=watchList,
            watchListLen=watchListLen,
        )
    else:
        abort(401)


@app.route("/login/", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/new/", methods=["GET"])
def new():
    # Render log in page
    return render_template("new.html")


@app.route("/list-item/", methods=["GET"])
def listItem():
    # Render log in page
    return render_template("list-item.html")


@app.route("/logged/", methods=["POST"])
def logged():
    # get user from the form
    user = request.form["username"]
    # get password from the form
    pwd = request.form["password"]

    # check if the input is blank, if yes redirect to login page
    if user == "" or pwd == "":
        return render_template("login.html")

    # check if users exists
    query = "SELECT * FROM auctions_user WHERE username = :user"
    rows = db.execute(query, user=user)

    # check if the hashed password match
    if verify_password(pwd, rows[0]["password"]):
        # start session
        session["user"] = user
        session["time"] = datetime.now()
        # store user id
        session["uid"] = rows[0]["id"]

        # get current timestamp
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

        # update last user login
        db.execute(
            "UPDATE auctions_user SET last_login = :last_login WHERE username = :user",
            last_login=ts,
            user=user,
        )

        # redirect to homepage
        return redirect("/")
    return render_template("login.html", msg="Wrong username or password.")


@app.route("/logout/")
def logout():
    # clear Session
    session.clear()
    # redirect to homepage
    return redirect("/")


@app.route("/register/", methods=["POST"])
def registration():
    # get data from the form
    username = request.form["username"]
    password = request.form["password"]
    fname = request.form["fname"]
    lname = request.form["lname"]
    email = request.form["email"]

    # check if username already in the database
    rows = db.execute(
        "SELECT * FROM auctions_user WHERE username = :username ", username=username
    )

    # send error if user exists
    if len(rows) > 0:
        return render_template("new.html", msg="Username already exists!")

    # get timestamp
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

    # insert user into database
    db.execute(
        "INSERT INTO auctions_user (username, password, first_name, last_name, email, is_superuser, is_staff, is_active, date_joined) VALUES (:username, :password, :first_name, :last_name, :email, 0, 0, 0, :time)",
        username=username,
        password=hash_password(password),
        first_name=fname,
        last_name=lname,
        email=email,
        time=ts,
    )

    # redirect to login page
    return render_template("login.html")


@app.route("/add-item/", methods=["POST"])
def addItem():
    if session:
        # get item title
        bidTitle = request.form["bidTitle"]

        # get item description
        bidDescription = request.form["bidDescription"]

        # check get uploaded file
        uploaded_file = request.files["file"]
        if uploaded_file.filename != "":
            # check filename if secure
            filename = secure_filename(uploaded_file.filename)
            file_ext = os.path.splitext(filename)[1]

            # check file extension as well if the content is really an image
            if file_ext not in app.config[
                "UPLOAD_EXTENSIONS"
            ] or file_ext != validate_image(uploaded_file.stream):
                abort(400)
            uploaded_file.save(os.path.join(app.config["UPLOAD_PATH"], filename))
        # get the starting bid
        startingBid = request.form["startingBid"]

        # full image path
        full_path = "/static/img/" + uploaded_file.filename

        # get timestamp
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")

        # insert item into database
        db.execute(
            "INSERT INTO auctions_listing (datetime, title, description, currentBidValue, imageURL, isOpen, user_id, winner_id) VALUES (:time, :title, :description, :currentBidValue, :imageURL, 1, :user_id, 1)",
            time=ts,
            title=bidTitle,
            description=bidDescription,
            currentBidValue=startingBid,
            imageURL=full_path,
            user_id=session["uid"],
        )
    return index()
