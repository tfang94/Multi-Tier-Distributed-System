[![Open in Visual Studio Code](https://classroom.github.com/assets/open-in-vscode-c66648af7eb3fe8bc4f294546bfd86ef473780cde1dea487d3c4ff354943c9ae.svg)](https://classroom.github.com/online_ide?assignment_repo_id=7774249&assignment_repo_type=AssignmentRepo)
Compsci 677: Distributed and Operating Systems

Spring 2022

# Lab 3: Caching, Replication and Fault Tolerance

## Team Members

You may work in groups of 2 for this lab assignment. Please list the names of the group members
here. You may replace this readme file with your own documentation, in which case, please list the
names of all team members at the top of the readme.

## Goals and Learning Outcomes

The lab has the following learning outcomes with regards to concepts covered in class.

* Learn about caching, replication, and consistency.
* Learn about the concepts of fault tolerance and high availability.
* Learn about how to deploy your application on the cloud.

## Lab Description

This project is based on lab 2. You can reuse some of the code you wrote in lab 2 if you want. You
are going to add caching, replication, and fault tolerance to the toy store application that we have
implemented in the previous labs. Here are some basic requirements:

1.  The toy store application consists of three microservices: a front-end service, a catalog
    service, and an order service.

2.  The front-end service exposes the following REST APIs as they were defined in lab2:

    *   `GET /products/<product_name>`
    *   `POST /orders`

    In addition, the front-end service will provide a new REST API that allows clients to query
    existing orders:

    *   `GET /orders/<order_number>`

        This API returns a JSON reply with a top-level `data` object with the three fields:
        `number`, `name`, and `quantity`. If the order number doesn't exist, a JSON reply with a
        top-level `error` object should be returned. The `error` object should contain two fields:
        `code` and `message`

    Since in this lab we will focus on higher level concepts, you can use a web framework like
    [`Django`](https://github.com/perwendel/spark), [`Flask`](https://github.com/pallets/flask),
    [`Spark`](https://github.com/perwendel/spark) to implement your front-end service. You can also
    reuse the code you wrote in lab 2 if you prefer.

3.  Like in lab 2, you can decide the interfaces used between the microservices. Each microservice
    still need to be able to handle requests concurrently. You can use any concurrency models
    covered in class.

4.  Add some variety to the toy offering by initializing your catalog with at least 10 different
    toys( You can consider adding some toys from the [National Toy Hall of
    Fame](https://en.wikipedia.org/wiki/National_Toy_Hall_of_Fame)). Each toy should have an initial
    stock of 100. Also the catalog service will periodically restock the toys that are out of stock.
    The catalog service should check remaining quantity of every toy every 10 seconds, if a toy is
    out of stock the catalog service will restock it to 100.

5.  The client first queries the front-end service with a random toy. If the returned quantity is
    greater than zero, with probability p it will send an order request (make p an variable that's
    adjustable). You can decide whether the the toy query request and the order request uses the
    same connection. The client will repeat for a number of iterations, and record the the order
    number and order information if a purchase request was successful. Before exiting, the client
    will retrieve the order information of each order that was made using the order query request,
    and check whether the server reply matches the locally stored order information.

## Part 1: Caching

In this part we will add caching to the front-end service to reduce the latency of the toy query
requests. The front-end server start with an empty in-memory cache. Upon receiving a toy query
request, it first checks the in-memory cache to see whether it can be served from the cache. If not,
the request will then be forwarded to the catalog service, and the result returned by the catalog
service will be stored in the cache.

Cache consistency needs to be addressed whenever a toy is purchased or restocked. You should
implement a server-push technique: catalog server sends invalidation requests to the front-end
server after each purchase and restock. The invalidation requests cause the front-end service to
remove the corresponding item from the cache.

## Part 2: Replication

To make sure that our toy store doesn't lose any order information due to crash failures, we want to
replicate the order service. When you start the toy store application, you should first start the
catalog service. Then you start three replicas of the order service, each with a unique id number
and its own database file. There should always be 1 leader node and the rest are follower nodes. You
do **NOT** need to implement a leader election algorithm. Instead the front-end service will always
try to pick the node with the highest id number as the leader.

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

In this part you will handle failures of the order service. In this lab you only need to deal with
crash failure tolerance rather than Byzantine failure tolerance.

First We want to make sure that when any replica crashes (including the leader), toy purchase
requests and order query requests can still be handled and return the correct result. To achieve
this, when the front-end service finds that the leader node is unresponsive, it will redo the leader
selection algorithm as described in [Part2](#part-2-replication).

We also want to make sure that when a crashed replica is back online, it can synchronize with the
other replicas to retrieve the order information that it has missed during the offline time. When a
replica came back online from a crash, it will look at its database file and get the latest order
number that it has and ask the other replicas what orders it has missed since that order number.

## Part 4: Testing and Evaluation with Deployment on AWS

First, write some simple test cases to verify that your code works as expected. You should test both
each individual microservice as well as the whole application. Submit your test cases and test
output in a test directory.

Next, deploy your application on an `m5a.xlarge` instance in the `us-east-1` region on AWS. We will
provide instructions on how to do this in homework 6. Run 5 clients on your local machine. Measure
the latency seen by each client for different type requests. Change the probability p of a follow up
purchase request from 0 to 80%, with an increment of 20%, and record the result for each p setting.
Make simple plots showing the values of p on the X-axis and the latency of different types of
request on the y-axis. Also do the same experiments but with caching turned off, estimate how much
benefits does caching provide by comparing the results.

Finally, simulate crash failures by killing a random order service replica while the clients is
running, and then bring it back online after some time. Repeat this experiment several times and
make sure that you test the case when the leader is killed. Can the clients notice the failures
(either during order requests or the final order checking phase) or are they transparent to the
clients? Do all the order service replicas end up with the same database file?

## What to submit

At the top of this README file add the name(s) and umass email address(es) of all the team members.
Also if you are working in a group, briefly describe how the work is divided.

You solution should contain source code for both parts separately. Inside the src directory, you
should have a separate folder for each component/microservice, e.g., a `client` folder for client
code, a `front-end` folder for the front-end service, etc.

A short README file on how to run your code. Include build/make files if you created any, otherwise
the README instructions on running the code should provide details on how to do so.

Submit the following additional documents inside the docs directory. 1) A Brief design document (1
to 2 pages) that explains your design choices (include citations, if you used referred to Internet
sources), 2) An Output file (1 to 2 pages), showing sample output or screenshots to indicate your
program works, and 3) An Evaluation doc (2 to 3 pages), for part 4 showing plots and making
observations.

## Grading Rubric

Parts 1-3 account for 70% of the total lab grade:

* Code should have inline comments (5%).
* GitHub repo should have adequate commits and meaningful commit messages (5%).
* Source code should build and work correctly (40%).
* A descriptive design doc should be submitted (15%).
* An output file should be included (5%).

Parts 4 account for 30% of the total lab grade:

* Should provide steps in your eval docs about how you deployed your application on AWS. Include
  scripts in your repo if needed (5%).
* An eval doc with measurement results and plots (15%).
* Analysis of the results and answers to the questions in part 3 (10%).
