# Installation Process for Neo4j in Raspberry Pi 4

## First, get java

```
sudo apt update
sudo apt install default-jdk
java -version
```

## Downloading and Installing Neo4j


Go to Neo4j web page and download the **community version** for linux/mac (tar) file. This link wll take you there:

https://neo4j.com/download-center/#community

Create a directory where you want to place the Neo4j directory. *replace MY_PATH with your desired path.*
```
mkdir MY_PATH/NEO4J
```
Now let's install neo4j from the apt package manager:
```
sudo apt-get update
sudo apt-upgrade
sudo apt-get install neo4j
```
**Cut and paste** the .tar file downloaded from Neo4j web page into the newly created folder (NEO4J).

## Unzipping the files and Configuring Neo4J

Unzip the tar file:

```
cd MY_PATH/NEO4J
tar -xvf neo4j-community-4.0.3-unix.tar.gz 
cd neo4j-community-4.0.3/
```
*Please note that the name of the actual files may vary since the version changes with time. Fix these lines with your file names if different.*

Now, to fix the WARNING: Max 1024 open files allowed, minimum of 40000 recommended, modify limits.conf:
```
sudo nano /etc/security/limits.conf
```
Paste this at the end of the file:
```
root    soft    nofile  40000
root    hard    nofile  40000
neo4j   soft    nofile  40000
neo4j   hard    nofile  40000
```
CTRL + X to exit the nano editor. Press Y to save the changes, and press ENTER to confirm. 

It's time to make sure that our database is going to be stored in our desired directory. First, let's create our folder:
```
touch DBs
```
*Please note that I am naming this folder "DBs", but you can name it however you want. Just try to avoid spaces!*

Now, modify neo4j.conf like this:
```
cd conf
sudo nano neo4j.conf
```

Uncomment and modify this line like this:

```
dbms.directories.data=MY_PATH/NEO4J/DBs/
```
*Remember to change MY_PATH for your actual directory path. Also "DBs" if your are using a different name.*

Also, uncomment and modify this line to you disered name (OPTIONAL):

```
dbms.default_database=MY_DATABSE_NAME
```

Let's also allow automatic upgrades by simply uncommenting this line:

```
dbms.allow_format_migration=true
```

CTRL + X to exit the editor. Press Y to save changes, and press ENTER to confirm.

## One Last Step!!

One last step. Let's make sure that our modifications are going to be applied by telling Raspbian that our home directory for Neo4j is the one we just setup:

```
export NEO4J_HOME = MY_PATH/NEO4J/neo4j-community-4.0.3
export PATH=$NEO4J_HOME/bin:$PATH
```
*Remember to change MY_PATH for your actual directory path*

And that's it!! Now let's just start neo4j like this:

```
neo4j start
```