#importing necesssary libraries
import os 
import json 
from flask import Flask 
from flask import render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy 

from werkzeug.utils import secure_filename #library used for storing the images as filename

import datetime 
from sqlalchemy import DateTime, or_
from sqlalchemy.sql import func 

upload_folder = './static/imageupload' #path of the folder where images will be stored is being stored in a variable 

current_dir = os.path.abspath(os.path.dirname(__file__)) #path of the current directory

app = Flask(__name__) #creating of app
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///"+os.path.join(current_dir+'/directory', "bloglite.db") 
app.config['upload_folder'] = upload_folder

db = SQLAlchemy() 
db.init_app(app) 
app.app_context().push() 

ALLOWED_EXTENSIONS = ['png','jpg','jpeg','gif','jfif'] #only pictures with these extensions will be allowed to upload
def allowed_file(filename): # function which checks whether the uploaded file extension is valid or not
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#creation of models according to the tables made in the database

class User(db.Model): #user model for table model
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, autoincrement = True, primary_key = True)
    username = db.Column(db.String, unique = True)
    password = db.Column(db.String)
    followers = db.Column(db.Integer)
    posts = db.Column(db.Integer)
    photo = db.Column(db.String)

class Blog(db.Model): #blog model for table blog 
    __tablename__ = 'blog'
    post_id = db.Column(db.Integer, autoincrement = True, primary_key = True)
    title = db.Column(db.String)
    caption = db.Column(db.String)
    image = db.Column(db.String)
    timestamp = db.Column(DateTime, default = datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    username = db.Column(db.String, db.ForeignKey("user.username"))
    private = db.Column(db.Integer)

class Relation(db.Model): #relation model for table relation
    __tablename__ = 'relation'
    relation_id = db.Column(db.Integer, autoincrement = True, primary_key = True)
    id_follower = db.Column(db.Integer)
    id_following = db.Column(db.Integer)
    username_follower = db.Column(db.String)
    username_following = db.Column(db.String)



@app.route('/', methods=['GET','POST']) #routing for the index page on the start of application
def index():
    session['user_log'] = None #initialising the session for the user
    return render_template('index.html')

@app.route('/login', methods=['GET','POST']) #routing for login into the application
def user_login():
    if request.method =='GET':
        return render_template('index.html') #rendering the index page if get request is received
    else:
        if session['user_log'] is None:  #inputting the user credentials and checking if it exists then logs into application.
            u = User()
            u.username = request.form['username']
            u.password = request.form['password']
            user_nm = User.query.filter_by(username=u.username).first() #storing the first entry
            if user_nm is not None: 
                if user_nm.password == u.password:
                    #storing the credentials for the current user
                    session['user_log']={'id':user_nm.user_id,'username':user_nm.username,'password':user_nm.password,'followers':user_nm.followers,'posts':user_nm.posts}
                    result = Relation.query.filter_by(id_follower=session.get('user_log')['id']).all()

                    return redirect('/homepage')
                else:
                    return render_template('invalid.html'),400
            else:
                return render_template('invalid.html'),400
        else:
            return render_template('index.html')

@app.route('/signup',methods=['GET','POST']) #routing when signup of user is executed
def signup():
    if request.method=='GET':
        return render_template('signup.html')
    else:
        s = User()  #taking user credentials
        s.username = request.form['username']
        s.password = request.form['password']
        s.followers = 0
        s.posts = 0
        photo = request.files['photo']
        

        if User.query.filter_by(username = s.username).count()>0: #checking whether the username doesn't already exists
            return render_template('invalid.html')
        else:

            if photo and allowed_file(photo.filename): #checking for valid photo extension
                s.photo = photo.filename 
                photoname = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['upload_folder'], photoname))

            db.session.add(s) 
            db.session.commit()
            db.session.refresh(s)

            return redirect('/login')

@app.route('/homepage',methods=["GET"]) #routing for homepage after logging in 
def homepage():
    if session['user_log'] is not None: 
        #process for displaying the posts of the users whom the current user follows
        result = Relation.query.filter_by(id_follower = session.get('user_log')['id']).all()
        followingidList=[]
        for item in result:
            followingidList.append(item.id_following)
        blogList=Blog.query.filter(Blog.user_id.in_(followingidList)).order_by(Blog.timestamp.desc()).filter_by(private=0).all()
        print(blogList)
        return render_template("homepage.html", blogList = blogList, username = session.get('user_log')['username'])
    else:
        return redirect('/')

@app.route('/addpost', methods=["GET","POST"]) #routing for creation of a new post
def addpost():
    if request.method=="POST":
        b = Blog() 
        b.title = request.form['title']
        b.caption = request.form['caption']
        file = request.files['image']
        b.image = file.filename 
        b.user_id = session.get('user_log')["id"]
        b.username = session.get('user_log')["username"]
        b.private = request.form['privatecheck']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['upload_folder'], filename))
        
        db.session.add(b) 
        User.query.filter_by(user_id=session.get("user_log")["id"]).update({'posts':User.posts+1}) #incrementing the count of posts in the user table
        db.session.commit()
        db.session.refresh(b) 
        return redirect('/homepage')
    else:
        return render_template('addpost.html')

@app.route('/updateprofile/<int:user_id>', methods=['GET','POST']) #routing for updating the profile of the user
def updateprofile(user_id):
    if request.method == 'GET':
        u = User.query.get(user_id)
        return render_template('updateprofile.html',user = u)
    else:
        u = User.query.get(user_id)        
        stusername = request.form['username']       #used a separate variable just for checking condition 
        photo = request.files['photo']

        if User.query.filter_by(username = stusername).count()>0:
            return render_template('invalid.html')
        else:
            #earlier values are passed to htmlpage and the segments where new entries are recieved are being updated
            if photo and allowed_file(photo.filename):
                u.photo = photo.filename 
                photoname = secure_filename(photo.filename)
                photo.save(os.path.join(app.config['upload_folder'], photoname))
            Relation.query.filter_by(username_follower = u.username).update({'username_follower':stusername})
            Relation.query.filter_by(username_following = u.username).update({'username_following':stusername})
            u.username = request.form['username']
            u.password = request.form['password']
            db.session.commit()
            #updating the values in the session of the current user
            session['user_log']={'id':u.user_id,'username':u.username,'password':u.password,'followers':u.followers,'posts':u.posts,'photo':u.photo}

            return redirect('/myprofile')
            

        

@app.route('/updatepost/<int:post_id>',methods=["GET","POST"])#routing for updation of the posts
def updatepost(post_id):
    if request.method == "POST":
        b = Blog.query.get(post_id)
        b.title = request.form['title']
        b.caption = request.form['caption']
        file = request.files['image']
        
        b.user_id = session.get('user_log')["id"]
        b.username = session.get('user_log')["username"]
        b.private = request.form['privatecheck']
        
        #sending the previous values to the html page and then receiving the changed values and updating
        if file and allowed_file(file.filename):
            b.image = file.filename 
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['upload_folder'], filename))
        
        db.session.commit()

        return redirect('/myprofile')
    else:
        b = Blog.query.get(post_id)
        return render_template('updatepost.html',blog = b)


@app.route('/deletepost/<int:post_id>',methods = ['GET','POST']) #routing for deletion of the post
def deletepost(post_id):
    if request.method == 'POST':
        Blog.query.filter_by(post_id = post_id).delete()
        User.query.filter_by(user_id = session.get('user_log')['id']).update({'posts':User.posts-1}) #decreasing the value of post count from user table
        db.session.commit()
        return redirect('/myprofile')
    else:
        return render_template('deleteblog.html',post_id = post_id)    

@app.route('/logout',methods = ['GET','POST']) #routing for logging out
def logout():
    session['user_log']=None #closing the session for the current user
    return redirect('/')

@app.route('/searchuser',methods=["POST"]) #routing for seraching another user
def searchuser():
    su = request.form['search']
    search_user = User.query.filter(User.username.contains(su)).all() #all those entries whose username contains the searched letters
    print(search_user)
    return render_template('search.html',search_list=search_user, userid=session.get('user_log')['id'])

@app.route("/followsearch/<int:user_id>/<string:username>", methods = ["GET"]) #routing for following the search user
def followsearch(user_id,username):
    flag = True 
    result = len(Relation.query.filter_by(id_follower=session.get('user_log')['id'],id_following=user_id).all())
    if result==0:
        flag = False 
    return render_template('following.html',username=username, userid =user_id, flag = flag)

@app.route("/userfollow/<int:user_id>/<string:username>", methods = ["GET"])
def userfollow(user_id,username): #routing for following user
    relation = Relation()
    relation.id_follower = session.get('user_log')['id']
    relation.id_following = user_id 
    relation.username_follower = session.get('user_log')['username']
    relation.username_following = username 

    db.session.add(relation) 
    User.query.filter_by(user_id=user_id).update({'followers':User.followers+1})
    blogList  = Blog.query.filter_by(user_id = session.get('user_log')['id']).all()
    db.session.commit() 
    
    return redirect('/homepage')

@app.route("/userunfollow/<int:user_id>/<string:username>", methods = ["GET"]) #routing for unfollowing user
def userunfollow(user_id,username):
    result = Relation.query.filter_by(id_follower= session.get('user_log')['id'],id_following = user_id).delete()
    User.query.filter_by(user_id=user_id).update({'followers':User.followers-1})
    blogList  = Blog.query.filter_by(user_id = session.get('user_log')['id']).all()
    db.session.commit()

    return redirect('/homepage')

@app.route('/myprofile',methods = ['GET']) #routing for profile of the logged user
def myprofile():
    post_total = Blog.query.filter_by(user_id=session.get('user_log')['id']).count()
    following = Relation.query.filter_by(id_follower = session.get('user_log')['id']).count()
    followers = Relation.query.filter_by(id_following = session.get('user_log')['id']).count()
    blogList  = Blog.query.filter_by(user_id = session.get('user_log')['id']).all()
    user=User.query.get(session.get("user_log")["id"])
    return render_template('myprofile.html',username =session.get('user_log')['username'], following = following,followers =followers,post_total = post_total,blogList = blogList,user=user)

@app.route('/followinglist',methods = ['GET'])
def followinglist():
    following = Relation.query.filter_by(id_follower=session.get('user_log')['id']).all()
    return render_template('followinglist.html',following=following,username = session.get('user_log')['username'])

@app.route('/unfollowfollowing/<int:id_following>',methods = ['GET'])
def unfollowfollowing(id_following):
    Relation.query.filter_by(id_follower = session.get('user_log')['id'],id_following = id_following).delete()
    User.query.filter_by(user_id = id_following).update({'followers':User.followers-1})
    db.session.commit()
    return redirect('/followinglist')


@app.route('/followerslist',methods =['GET'])
def followerslist():
    follow_user = Relation.query.filter_by(id_follower = session.get('user_log')['id']).all()
    mapping = {}

    for item in follow_user:
        mapping[item.id_following] = item.id_follower 
    print(mapping)

    followers = Relation.query.filter_by(id_following = session.get('user_log')['id']).all()
    return render_template('followerlist.html',followers =followers,username = session.get('user_log')['username'],userid = session.get('user_log')['id'],mapping = mapping)

@app.route('/followfollower/<int:id_follower>/<string:username_follower>',methods = ['GET'])
def followfollower(id_follower,username_follower):
    r = Relation()
    r.id_follower = session.get('user_log')['id']
    r.id_following = id_follower 
    r.username_follower = session.get('user_log')['username']
    r.username_following = username_follower 
    db.session.add(r)
    User.query.filter_by(user_id = id_follower).update({'followers':User.followers+1})
    db.session.commit()
    return redirect('/followerslist') 

@app.route('/removefollower/<int:id_follower>',methods = ['GET'])
def removefollower(id_follower):
    Relation.query.filter_by(id_follower=id_follower, id_following = session.get('user_log')['id']).delete()
    User.query.filter_by(user_id = session.get('user_log')['id']).update({'followers':User.followers-1})
    db.session.commit() 
    return redirect('/followerslist')

@app.route("/guestprofile/<int:user_id>",methods = ["GET"]) #routing for profile of other users on the app
def guestprofile(user_id):
    post_total = Blog.query.filter_by(user_id=user_id).count()
    following = Relation.query.filter_by(id_follower = user_id).count()
    followers = Relation.query.filter_by(id_following = user_id).count()
    blogList  = Blog.query.filter_by(user_id = user_id).all()
    user=User.query.get(user_id)
    return render_template('guestprofile.html',username =session.get('user_log')['username'], following = following,followers =followers,post_total = post_total,blogList = blogList,user=user)

@app.route('/deleteaccount/',methods=['GET','POST'])
def deleteaccount():
    if request.method == 'GET':
        return render_template('deleteaccount.html')
    else:
        user_id = session.get('user_log')['id']
        Blog.query.filter_by(user_id = user_id).delete()
        Relation.query.filter_by(id_follower = user_id ).delete()
        Relation.query.filter_by( id_following = user_id).delete()
        User.query.filter_by(user_id = user_id).delete()

        db.session.commit()
        return redirect('/logout')

if __name__ == '__main__':
    app.secret_key = 'pd'
    app.debug = True 
    app.run()