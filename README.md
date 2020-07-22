# A Basic Bitcoin Block Explorer Built in Python

This is a project still in the developing phase.

This is project aims to be a Bitcoin block explorer with an API which is going to be used in the other project repository Blockchain specifically for the Bitcoin Wallet.

## Description

The Bitcoin blockchain is built on binary files which include a certain number of blocks. Each block contains transactions, which also contains the Bitcoins. In this way, the blockchain knows how many bitcoins are available and how they can be spent. However, due to space efficiency reasons, the blockchain can't be queried directly since it is binary information concatenated together. 

In order for somebody to interprete these binary files, it is necessary to decode these files into transactions, and blocks, according to the guidelines offered by the Bitcoin-core project.

In this order of ideas, this project decodes these binary files of the blockchain locally, and then creates a graph database that stores the whole interpreted blockchain. The purpose of this transition, is to be able to query the blockchain to conduct transactions, retrieve balances, etc. in a timely manner.

After, the blockchain is totally parsed into a graph database, we can serve this database to be queried by any client with the credentials to query the blockchain.

## Technical General Context

1. This project relies on a Full Bitcoin Node to operate. This project is being implemented on Raspberry Pies to run the full node, and also to decode and store the blockchain into a graph database.

2. This project needs a considerable amount of computing resources in order to conduct the blockchain parsing in a timely manner. This is why a Raspberry Pi cluster is being implemented to carry out this parsing in order to take advantage of multiprocessing, multithreading, and concurrency for efficiency purposes.

3. The type of database used in this project is a graph database called Neo4j. The reason for this selection is that a graph database is a natural fit for this project since the atomic unit of the blockchain and the graph databse is the transaction.

## Requirements

- Bitcoin full node.
- Neo4j graph database engine.
- Neo4j python driver ```pip install neo4j```
- 4 Terabytes of free space.

# Technical Details

- This project can rely on multiple computing units such as Raspberry Pies to parse chunks of the blockchain concurrently using multiprocessing. Python doesn't allow multiprocessing natively, which is why the parser needs to be called from outside n amount of times (n being the amount of cores of the computing unit). In this way, every time the process starts, it will do in a different core of the computing unit allowing multiprocessing. Also, this can be done in a single computing unit, but this will mean a slower parsing process.

- Multithreading is used in this project to speed up the process. Multithreading happens to avoid the python code to remain idle while waiting for the graph database to create the transactions that it was given. In this way, the python code will keep working on a thread while the graph databse will work on anotherone. 

- File-cursor is an important aspect in this project. Since it is possible, for technical or non-technical reasons, that the code will stop working abruptly, it is important to keep track of where, in the binary file, the parser stopped working. This way, next time the project starts parsing, it will pick up where it stopped last time, avoiding parsing twice transactions that had been already parsed. For this reason, this project contains a folder named "cursors" that stores the plain text files that contains where the parser is at the moment. This part of the code was developed from scratch.

- Logging is also important to trace errors. This project uses the Python native logging library using rotation to save space on disk.

- The graph database will create the following nodes: blocks, transactions, addresses, transaction-outputs (UTXOs).

## How to use

This project is still in the prototype phase, but it is still possible to parse a big chunk of the Bitcoin blockchain. 

First make sure the Neo4j database is running. Then  and then simply open the file block_parser.ipynb and make sure to change the user and password for the database to your own. After that, simply run the first 7 cells of the Jupyter notebook. 

This is how chunks of the blockchain looks like in a graph database:



<img src="images/01.png" width="800"/> 


- Red nodes: blocks
- Brown nodes: transactions
- Green nodes: UTXOs (bitcoins)



