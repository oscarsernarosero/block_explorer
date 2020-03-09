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
            let script = "";
            let firstvarint = read_varint(deobfuscated_value);
            height = firstvarint[0];
            pointer += firstvarint[1];
            secondvarint = read_varint(subarray(deobfuscated_value, pointer+1,deobfuscated_value.length-1,false));
            amount = secondvarint[0];
            pointer += firstvarint[1];
            let script_type = deobfuscated_value[pointer+1] + deobfuscated_value[pointer+2];



            let index = str[35] + str[36];
            console.log('%s = %s \ntype: %s \nTx ID: %s\nIndex : %s\nDeobfucated Value: %s \nHieght: %s \nAmount: %s \nType: %s', 
            data.key, data.value, type, tx_id, index_out, deobfuscated_value, height, amount, script_type); 
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