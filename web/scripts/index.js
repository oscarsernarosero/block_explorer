
var level = require('level');
//var path = require('path');


var first_entry = true;
var obf_key = "";
//const output = document.getElementById('output');
//output.innerHTML = "deobfuscated_value";

//main();

//function main(){
            console.log("index.js starting... main");
        var options = {    
            keyEncoding: 'hex',  
            valueEncoding: 'hex'  
        };


        var db = level("./chainstate_copy_test",options);

        var stream = db.createReadStream();

        stream.on('data', function(data) {  
            
            if (first_entry){
            //if (first_entry){
                obf_key = subarray(data.value,2,data.value.length-1,false);
                //obf_key = data.value;
                
                console.log(data.key);
                console.log("obf key "+obf_key);
                if (data.key == "0e006f62667573636174655f6b6579"){first_entry=false;}
            }else if (!first_entry){
            
            str = data.key;
            let type = str[0]+str[1];
            let tx_id = subarray(str, 2, 66, true);
            console.log(tx_id);
            let index_out = str[66] + str[67];
            let xtended_obf_key = get_obf_key(data.value.length, obf_key);
            let deobfuscated_value = string_xor(xtended_obf_key,data.value);
            let pointer = 0;
            let height = 0;
            let coinbase = false;
            let amount = 0;
            let firstvarint = decompress_varint(deobfuscated_value);
            if (parseInt("0x"+firstvarint[0])%2==1){coinbase=true;}
            height = parseInt("0x"+firstvarint[0])>>1;
            pointer = firstvarint[1];
            secondvarint = decompress_varint(subarray(deobfuscated_value, pointer,deobfuscated_value.length-1,false));
            amount = decompress_amount( parseInt("0x"+secondvarint[0]));
            pointer += firstvarint[1];
            type = subarray(deobfuscated_value, pointer+1,pointer+3,false);
            //let script_type = deobfuscated_value[pointer+1] + deobfuscated_value[pointer+2];

            console.log('%s = %s \ntype: %s \nTx ID: %s\nIndex : %s\nDeobfucated Value: %s \nHieght: %s \nAmount: %s \n', 
            data.key, data.value, type, tx_id, index_out, deobfuscated_value, height, amount); 
            //output.innerHTML = "deobfuscated_value";
            }
        });
//}

  function read_varint(s){
  //'''read_varint reads a variable integer from a stream'''
  const i = s[0]+s[1];
  if (i == "fd"){
      //# 0xfd means the next two bytes are the number
      return [subarray(s,2,5, true),6];}
  else if (i == "fe"){
      //# 0xfe means the next four bytes are the number
      return [subarray(s,2,9,true),10];}
  else if (i == 0xff){
      //# 0xff means the next eight bytes are the number
      return [subarray(s,2,17,true),18];}
  else{
      //# anything else is just the integer
      return [i,2];}
    }


    function subarray(array, start, end, reverse){
        console.log("array length: " + (end-start+1));
        let temp = new Array(end-start+1);
        
        for (let i=0;i<(end-start);i+=2){
            if (reverse == false){
                temp[i] = array[start+i];
                temp[i+1] = array[start+i+1];
            }else{
                temp[end-i-1] = array[start+i];
                temp[end-i] = array[start+i+1];
            }
            //console.log(temp);
        }
        return temp.join("");

    }


    function get_obf_key(value_length, obf_key){
        //obf_key ="b12dcefd8f872536";
        console.log(obf_key);

        xtended_obf_key =obf_key;
        counter= 0;

        while(xtended_obf_key.length<value_length){
            //console.log(xtended_obf_key);
            xtended_obf_key += obf_key[counter];
            counter +=1;
            if (counter>=obf_key.length){counter = 0;}

        }
        return xtended_obf_key;
    }

    function string_xor(str1,str2){

        const n = BigInt("0x"+str1);
        const m = BigInt("0x"+str2);

        const xor = (m ^ n).toString(16);
        console.log("extended obfuscated key: "+n.toString(16));
        console.log("xor: "+xor);

        return xor;
    }

    function decompress_varint(hex_str){
        console.log("hex_str: "+hex_str);

        let last = false;
        let amount = new Array(0);
        let most_significant = true;
        let bit_storeA = 0;
        let size = 0;
        let pointer = 1;
        let most_sig_half = 0;
        let current = "";
        let bit_storeB=0;

        for (let i=0;i<hex_str.length;i++){
            if (last && i%2==0){
                break;
            }else if(i%2==0){
                size++;
                let num = parseInt("0x0"+hex_str[i]);
                console.log("size num: "+num);
                if (num < 8){
                    console.log("found last: "+num);
                    last=true
                }
            }
        }

        pointer = size*2;
    console.log("size: "+size);
        

        for (let i=0;i<hex_str.length;i++){

            let num = parseInt("0x0"+hex_str[i]);
            console.log("num: "+num);

            if (size > 1){

                if (most_significant){
                    num = num & 7;
                    amount.push(num);//amount= 
                    console.log("amount after push mostsignificant: "+amount);
                    most_significant = false;
                }else{
                    most_sig_half = amount[amount.length-1];
                    console.log(most_sig_half);
                    num++;
                    current = most_sig_half<<4 | num;

                    bit_storeB =0;

                    for (let bit=0;bit<size-1;bit++){
                        if (current%2!=0){
                            bit_storeB+=Math.pow(2,bit);
                        }
                        current = current>>1;
                    }
                    current = current | bit_storeA<<(8-size);
                    console.log(current);
                    bit_storeA = bit_storeB;

                    amount[amount.length-1] = current;
                    console.log("amount after push byte: "+amount);
                    most_significant = true;
                    size--;
                    
                }
        }else{
            if (most_significant){
                amount.push(num);
                console.log("amount after push mostsignificant last byte: "+amount);
                most_significant = false;
            }else{
                most_sig_half = amount[amount.length-1];
                current = most_sig_half<<4 | num;
                current = current | bit_storeA<<(8-size);
                amount[amount.length-1] = current;
                console.log("amount after push byte final: "+amount);

                console.log("amount berfore str: "+amount);
                let amount_str = "";
                    for (let n=0;n<amount.length;n++){
                        console.log("converting "+amount[n]+" to string")
                        if (amount[n]<=15){
                            amount_str += ("0"+amount[n].toString(16));
                        }else{ 
                            amount_str += amount[n].toString(16);
                        }
                        console.log("varint string: "+amount_str);
                    }
        
                return [amount_str, pointer];
                
            }
        }

        }
        
    }

    function decompress_amount(amount){
        let exponent = 0;
        if (amount == 0){
            return 0;
        }

        amount--;
        exponent = amount%2;
        amount = parseInt(amount/10);

        let n = 0;
        if (exponent <9){
            d = amount%9 +1;
            amount = parseInt(amount/9);
            n = amount*10 + d;
        }else{
            n = amount + 1;
        }

        for (let x=0;x<exponent;x++){
            n*=10;
        }

        return n;

    }