import json

resolution_choice = input('Video resolution choices:\n1: 1920x1080,30p\t2:1280x720,60p\t 3:1280x720,30p.\tYour choice: ')

res_dic = {
    '1': ('1920x1080','30p'),
    '2: ('1280x720','60p'),
    3: ('1280x720','30p'),
}

print(res_dic['resolution_choice'])