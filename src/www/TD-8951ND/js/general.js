function doValidIPAndMask(Address, Mask, Where)
{
	if((Address == "") && (Mask != ""))
	{
		if(Where == 1){
		alert("Invalid destination IP address: " + Address);		}else if(Where == 2){
		alert("Invalid Source IP Address: "+Address);		}else {
   		alert("IP address is empty or wrong format!");		}	    	        				         
        return false; 
	}
	else if((Address != "") && (Mask == ""))
	{
		if(Where == 1){
		alert("Invalid Destination network mask!");		}else if(Where == 2){
		alert("Invalid Source network mask!");		}else{
   		alert("Invalid subnet mask: " + Mask);		}     	  
	  	return false;
	}
	else
		return true;
} 

function chineseCheck(object, objectId)
{
	var obj = document.getElementById(objectId);
	var objName = obj.innerText;
	var inputStr = object.value;
	var i;
	
	if(objName == undefined)
		objName = "Warning : input";
	for(i = 0; i < inputStr.length; i++)
	{
		if(inputStr.charCodeAt(i) < 0 || inputStr.charCodeAt(i) > 255)
		{
		alert(objName + " can not contains character which not ASCII!!");			return true;
		}
	} 
	return false;
}

function navigationFontChange(divName)
{
	return;
}

function doVCChange(value) {
document.Alpha_WAN.wanVCFlag.value = 1;
//document.Alpha_WAN.submit();

 if(value==0)
  {
  document.Alpha_WAN.Alwan_VPI.value=1;
  document.Alpha_WAN.Alwan_VCI.value=32;
  }
   if(value==1)
  {
  document.Alpha_WAN.Alwan_VPI.value=0;
  document.Alpha_WAN.Alwan_VCI.value=33;
  }
   if(value==2)
  {
  document.Alpha_WAN.Alwan_VPI.value=0;
  document.Alpha_WAN.Alwan_VCI.value=35;
  }
   if(value==3)
  {
  document.Alpha_WAN.Alwan_VPI.value=0;
  document.Alpha_WAN.Alwan_VCI.value=100;
  }
   if(value==4)
  {
  document.Alpha_WAN.Alwan_VPI.value=8;
  document.Alpha_WAN.Alwan_VCI.value=35;
  }
   if(value==5)
  {
  document.Alpha_WAN.Alwan_VPI.value=8;
  document.Alpha_WAN.Alwan_VCI.value=48;
  }
  if(value==6)
  {
  document.Alpha_WAN.Alwan_VPI.value=0;
  document.Alpha_WAN.Alwan_VCI.value=38;
  }

return;
}
