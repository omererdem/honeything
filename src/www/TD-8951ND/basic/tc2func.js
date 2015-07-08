// JavaScript Document
function unValidMask(Mask,Where)
{
var mask = Mask.match("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$");
var digits;
var bMask = 0;
var watch = false;
var i;
if(mask == null)
{
if(Where != 0 && Mask == "")
return false;
if(Where == 1){
alert("Invalid Destination network mask!");}else if(Where == 2){
alert("Invalid Source network mask!");}else{
alert("Invalid subnet mask: " + Mask);}
return true;
}
digits = mask[0].split(".");
if(digits.length != 4)
{
alert("Invalid subnet mask: " + Mask);return true;
}
for(i=0; i < 4; i++)
{
if(isNaN(digits[i]) || (Number(digits[i]) > 255 ) || (Number(digits[i]) < 0 ))
{
if(Where == 1){
alert("Invalid Destination network mask!");}else if(Where == 2){
alert("Invalid Source network mask!");}else{
alert("Invalid subnet mask: " + Mask);}
return true;
}
bMask = (bMask << 8) | Number(digits[i]);
}
if ( Where == 0 && Mask == "0.0.0.0")
{
if(Where == 1){
alert("Invalid Destination network mask!");}else if(Where == 2){
alert("Invalid Source network mask!");}else{
alert("Invalid subnet mask: " + Mask);}
return true;
}
bMask = bMask & 0x0FFFFFFFF;
for(i=0; i<32; i++)
{
if((watch==true) && ((bMask & 0x1)==0)) {
if(Where == 1){
alert("Invalid Destination network mask!");}else if(Where == 2){
alert("Invalid Source network mask!");}else{
alert("Invalid subnet mask: " + Mask);}
return true;
}
if((bMask & 0x01) == 1) watch=true;
bMask = bMask >> 1;
}
return false;
}
function isValidIpAddr(ip1,ip2,ip3,ip4) {
if(ip1==0 || ip4==255 || ip1==127)
return false;
return true;
}
function doValidateIP(Address, option1, option2, Where) {
var address = Address.match("^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$");
var digits;
var i;
if((option2 == 2) && Address == "0.0.0.0")
{
if(Where == 1){
alert("Invalid destination IP address: " + Address);}else if(Where == 2){
alert("Invalid Source IP Address: "+Address);}else {
alert("IP address is empty or wrong format!");}
return false;
}
if(((option1 == 1 || option1 == 4) && Address == "0.0.0.0") || (option1 == 2 && Address == "http://192.168.1.1/basic/255.255.255.255"))
return true;
if(address == null) {
if(option1 == 4 && Address == "")
return true;
if(Where == 1){
alert("Invalid destination IP address: " + Address);}else if(Where == 2){
alert("Invalid Source IP Address: "+Address);}else {
alert("IP address is empty or wrong format!");}
return false;
}
digits = address[0].split(".");
for(i=0; i < 4; i++) {
if(isNaN(digits[i]))
{
alert("IP address is empty or wrong format!");return false;
}
}
for(i=0; i < 4; i++) {
if((Number(digits[i]) > 255 ) || (Number(digits[i]) < 0 ) || (option1 != 4 && Number(digits[0]) > 223))
{
if(Where == 1){
alert("Invalid destination IP address: " + Address);}else if(Where == 2){
alert("Invalid Source IP Address: "+Address);}else{
alert("Invalid IP address: " + Address);}
return false;
}
}
if((!isValidIpAddr(digits[0],digits[1],digits[2],digits[3])) || (option1 == 3 && Address == "1.0.0.0") || (option2 == 1 && digits[3] == 0)) {
if(Where == 1){
alert("Invalid destination IP address: " + Address);}else if(Where == 2){
alert("Invalid Source IP Address: "+Address);}else{
alert("Invalid IP address: " + Address);}
return false;
}
return true;
}
function doValidateRange(startIP,endIP) {
var staddress;
var edaddress;
var cnt;
staddress=startIP.split(".");
edaddress=endIP.split(".");
for(cnt=0; cnt < 4; cnt++) {
if((cnt<3)&&( Number(edaddress[cnt])!= Number(staddress[cnt]) ) ){
alert("End IP address and Start IP address are not in the same subnet!");return false;
}
if( (cnt==3)&&( Number(edaddress[cnt]) < Number(staddress[cnt]) ) ){
alert("End IP address is less than Start IP address!");return false;
}
}
return true;
}
function isNumeric(s)
{
var len= s.length;
var ch;
if(len==0)
return false;
for( i=0; i< len; i++)
{
ch= s.charAt(i);
if( ch > '9' || ch < '0')
{
return false;
}
}
return true;
}
function doHexCheck(c)
{
if ( (c >= "0") && (c <= "9") )
return 1;
else if ( (c >= "A") && (c <= "F") )
return 1;
else if ( (c >= "a") && (c <= "f") )
return 1;
return -1;
}
function doMACcheck(object)
{
var szAddr = object.value;
var len = szAddr.length;
if ( len == 0 )
{
object.value ="00:00:00:00:00:00";
return;
}
if ( len == 12 )
{
var newAddr = "";
var i = 0;
for ( i = 0; i < len; i++ )
{
var c = szAddr.charAt(i);
if ( doHexCheck(c) < 0 )
{
alert("Invalid MAC Address");//      	object.value ="00:00:00:00:00:00";
object.focus();
return;
}
if ( (i == 2) || (i == 4) || (i == 6) || (i == 8) || (i == 10) )
newAddr = newAddr + ":";
newAddr = newAddr + c;
}
object.value = newAddr;
return;
}
else if ( len == 17 )
{
var i = 2;
var c0 = szAddr.charAt(0);
var c1 = szAddr.charAt(1);
if ( (doHexCheck(c0) < 0) || (doHexCheck(c1) < 0) )
{
alert("Invalid MAC Address");//      	object.value ="00:00:00:00:00:00";
object.focus();
return;
}
i = 2;
while ( i < len )
{
var c0 = szAddr.charAt(i);
var c1 = szAddr.charAt(i+1);
var c2 = szAddr.charAt(i+2);
if ( (c0 != ":") || (doHexCheck(c1) < 0) || (doHexCheck(c2) < 0) )
{
alert("Invalid MAC Address");//      		object.value ="00:00:00:00:00:00";
object.focus();
return;
}
i = i + 3;
}
return;
}
else
{
alert("Invalid MAC Address");//  		object.value ="00:00:00:00:00:00";
object.focus();
return;
}
}