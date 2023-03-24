[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-c66648af7eb3fe8bc4f294546bfd86ef473780cde1dea487d3c4ff354943c9ae.svg)](https://classroom.github.com/online_ide?assignment_repo_id=7774249&assignment_repo_type=AssignmentRepo)
# Multi-Tier Distributed Toy Store

I implemented a distributed client server toy store application during my Masters studies.  This was
a project for my Distributed & Operating systems class.  Besides some high level structural stipulations,
I had complete freedom on the particular implementation and everything was built from scratch.

The server side consists of a front-end service which communicates via REST api's with the 
client.  It also communicates with the backend service that includes a catalog and order service,
each maintaining their own databases.

I chose to use client-socket as my choice for RPC for communicating between frontend and backend services.
Some other functionality which are detailed further below include synchronization via read and write locks to 
ensure consistency during concurrent access, multi-threading with thread pool, fault tolerance via replication of
databases that automatically sync and update, caching to make for more efficient query requests.

## Instructions
1.  Clone repository

2.  Create new process for each microservice and execute in the following order: catalog_service.py, 
    order_service.py (for all 3 replicas), frontend_service.py, client.py.
    
    The default is to run all the services on the same machine, but it is a distributed system.  
    If running on different machines, update the host and port information.
    
    Optional command line arguments can also be entered to adjust and toggle some parameters.  See 
    individual files to see options.
    
    The client.py file will send multiple query and buy requests and will print out feedback from
    server side.  The server side can simulate database failures, and the fault tolerance system will
    deal with it.  One such simulation can be toggled with command line argument.  From the client side,
    the failure is not noticed.


## Functionality

1.  The toy store application consists of three microservices: a front-end service, a catalog
    service, and an order service.

2.  The front-end service exposes the following REST APIs:

    *   `GET /products/<product_name>`
    *   `POST /orders`
    *   `GET /orders/<order_number>`

3.  Each microservice can handle requests concurrently.  

4.  Catalog service includes a database (text file suffices for this scope) with 10 toys detailing 
    their price and quantity

5.  The client first queries the front-end service with a random toy. If the returned quantity is
    greater than zero, with probability p it will send an order request (p is adjustable command line arg). 
    The client will repeat for a number of iterations, and record the the order
    number and order information if a purchase request was successful. Before exiting, the client
    will retrieve the order information of each order that was made using the order query request,
    and check whether the server reply matches the locally stored order information.

## Part 1: Caching

Front-end service incorporates caching to reduce the latency of the toy query
requests. The front-end server start with an empty in-memory cache. Upon receiving a toy query
request, it first checks the in-memory cache to see whether it can be served from the cache. If not,
the request will then be forwarded to the catalog service, and the result returned by the catalog
service will be stored in the cache.

Cache consistency is addressed whenever a toy is purchased or restocked. It utilizes a server-push 
technique: catalog server sends invalidation requests to the front-end
server after each purchase and restock. The invalidation requests cause the front-end service to
remove the corresponding item from the cache.

## Part 2: Replication

To make sure that our toy store doesn't lose any order information due to crash failures, we 
replicate the order service. When you start the toy store application, you should first start the
catalog service. Then you start three replicas of the order service, each with a unique id number
and its own database file. There should always be 1 leader node and the rest are follower nodes. 
The front-end service will always try to pick the node with the highest id number as the leader.

When the front-end service starts, it will read the id number and address of each replica of the
order service (this can be done using configuration files/environment variables/command line
parameters). It will ping (here ping means sending a health check request rather than the `ping`
command) the replica with the highest id number to see if it's responsive. If so it will notify all
the replicas that a leader has been selected with the id number, otherwise it will try the replica
with the second highest id number. The process repeats until a leader has been found.

When a purchase request or an order query request, the front-end service only forwards the request
to the leader. In case of a successful purchase (a new order number is generated), the leader node
will propagate the information of the new order to the follower nodes to maintain data consistency.

## Part 3: Fault Tolerance

First We want to make sure that when any replica crashes (including the leader), toy purchase
requests and order query requests can still be handled and return the correct result. To achieve
this, when the front-end service finds that the leader node is unresponsive, it will redo the leader
selection algorithm.

We also want to make sure that when a crashed replica is back online, it can synchronize with the
other replicas to retrieve the order information that it has missed during the offline time. When a
replica came back online from a crash, it will look at its database file and get the latest order
number that it has and ask the other replicas what orders it has missed since that order number.

## Part 4: Testing and Evaluation

Multiple test cases are covered in src/Test Cases.  These ensure functionality of all the different
microservices along with testing for various invalid inputs.  Failure simulations to test for 
effectiveness of replicated fault tolerant catalog service is also included.

Within the docs/ folder includes design document along with evaluation and output files.  

