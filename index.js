var level = require('level')
var first_entry = true;
var obf_key = "";


var options = {    
    keyEncoding: 'hex',  
    valueEncoding: 'hex'  
  };
  

var db = level('./chainstate_copy_test',options)

var stream = db.createReadStream();

stream.on('data', function(data) {  
    
    if (first_entry){
        obf_key = data.value;
        first_entry=false;
    }
    
    str = data.key;
    let type = str[0]+str[1];
    let tx_id = subarray(str, 2, 66, true);
    console.log(tx_id);
    let index_out = str[66] + str[67];
    let xtended_obf_key = get_obf_key(data.value.length, obf_key);
    let deobfuscated_value = string_xor(xtended_obf_key,data.value);
    //let deobfuscated_value = ( parseInt(xtended_obf_key,16)^parseInt(data.value,16)).toString(16);
    //let deobfuscated_value = (xtended_obf_key  ^  data.value).toString(16);

    let index = str[35] + str[36];
    console.log('%s = %s \ntype: %s \nTx ID: %s\nIndex : %s\nValue: %s',
     data.key, data.value, type, tx_id, index_out, deobfuscated_value);  
  });

  function read_varint(s){
  //'''read_varint reads a variable integer from a stream'''
  let i = s[0];
  if (i == 0xfd){
      //# 0xfd means the next two bytes are the number
      return little_endian_to_int(s.read(2));}
  else if (i == 0xfe){
      //# 0xfe means the next four bytes are the number
      return little_endian_to_int(s.read(4));}
  else if (i == 0xff){
      //# 0xff means the next eight bytes are the number
      return little_endian_to_int(s.read(8));}
  else{
      //# anything else is just the integer
      return i;}
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

    async function string_xor(str1,str2){
        xor = "";
        end=0;
        for (let i=0;i*14<(str1.length);i++){
            start= i*14;
            console.log(i);
            console.log("length: "+str1.length);

            if (i*14+13 >= str1.length){end = str1.length-1;}
            else {end = i*14+13 ;}
            console.log("start "+start+" end "+end+" "+typeof end);

            xor = xor + ( parseInt(subarray(str1,start,end, false),16)^ 
                     parseInt(subarray(str2,start, end,false),16)   ).toString(16);
            console.log("xor: "+xor);
        }
        return xor;

    }