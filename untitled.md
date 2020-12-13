# Querie for block explorer:

## detailed transaction list of an address:

MATCH (a:address {address:"mo3WWB4PoSHrudEBik1nUqfn1uZEPNYEc8"})-[r]-(o)-[q]-(t) 
WITH t
MATCH (c:address)--(input:output)-[:SPENDS]->(t)
WITH t as tx, COLLECT(DISTINCT c.address) as in_addr, COLLECT(DISTINCT input.amount) as in_amount
MATCH (tx)-[:CREATES]-(output:output)--(d:address)
with tx,in_addr,in_amount,COLLECT(DISTINCT d.address) as out_addr,COLLECT(DISTINCT output.amount) as out_amount
RETURN in_addr,in_amount,tx, out_addr,out_amount


## DETAILED TRANSACTION LIST OF AN ADDRESS WITH BLOCK REWARDS:

MATCH (a:address {address:"tb1qyrtr6vc5kfh55mdjnvj59vlt8uupmrskmmu4tf"})-[r]-(o)-[c]-(t) 
WITH t
OPTIONAL MATCH (b:block)-[c:COINBASE]->(t)-[:CREATES]->(block_reward)
WITH t, COLLECT(DISTINCT b.id) as blocks, COLLECT(DISTINCT block_reward.amount) as block_reward_amount
OPTIONAL MATCH (c:address)--(input:output)-[:SPENDS]->(t)
WITH t as tx, blocks, block_reward_amount, COLLECT(DISTINCT c.address) as in_addr, COLLECT(DISTINCT input.amount) as in_amount
OPTIONAL MATCH (tx)-[:CREATES]-(output:output)--(d:address)
with tx,in_addr,in_amount,COLLECT(DISTINCT d.address) as out_addr,COLLECT(DISTINCT output.amount) as out_amount,block_reward_amount,blocks
RETURN in_addr,in_amount,tx, out_addr,out_amount,block_reward_amount,blocks

## total money of an address:

MATCH (a:address {address:"mo3WWB4PoSHrudEBik1nUqfn1uZEPNYEc8"})-[r]-(o)
WHERE NOT (o)-[:SPENDS]->()
RETURN SUM(o.amount)

# Fix stale forks:

MATCH (a:block)-[r:LINKS]->(b:block) WITH a, COUNT(r) AS links WHERE links>1 
WITH a
MATCH (a)-[r:LINKS]->(b:block)
WHERE NOT EXISTS(b.height)
DELETE r
return b

MATCH (b:block)-[r]-() WHERE NOT EXISTS(b.height) DELETE b,r

MATCH (o:output {index:4294967295})-[r]-()
DELETE o,r
