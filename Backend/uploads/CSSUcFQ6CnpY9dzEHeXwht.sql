create database text_to_sql;
use text_to_sql;
select * from customers; --  Customer Index
select * from sales_order; -- Customer Name Index

#what is the total 'Line Total' for Geiss Company?
select s.`Customer Name Index`, SUM(s.`Line Total`) from customers c, sales_order s
where c. `Customer Index` = s. `Customer Name Index`
and c. `Customer Names` = 'Geiss Company'
group by s. `Customer Name Index`;

SELECT `2017 Budgets` FROM `2017_budgets` WHERE `Product Name` = 'Product 12'