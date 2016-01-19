def get_default_if():
    """ Returns the default interface """
    f = open ('/proc/net/route', 'r')
    for line in f:
        words = line.split()
        dest = words[1]
        try:
            if (int (dest) == 0):
                interf = words[0]
                break
        except ValueError:
            pass
    return interf

def get_default_gw():
    """ Returns the default gateway """
    octet_list = []
    gw_from_route = None
    f = open ('/proc/net/route', 'r')
    for line in f:
        words = line.split()
        dest = words[1]
        try:
            if (int (dest) == 0):
                gw_from_route = words[2]
                break
        except ValueError:
            pass
        
    if not gw_from_route:
        return None 
    
    for i in range(8, 1, -2):
        octet = gw_from_route[i-2:i]
        octet = int(octet, 16)
        octet_list.append(str(octet)) 
    
    gw_ip = ".".join(octet_list)
            
    return gw_ip
