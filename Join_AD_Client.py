"""
该程序用于在客户端中输入计算机名，并将计算机自动加入域；
免输加域时的账号密码、如域服务器有重复的计算机名，则会自动删除重复的计算机；
批量登录域服务器，并自动删除多台域服务器中的重复计算机，目的是让计算机能顺利加入域；
由于导入其它模块速度较慢，因此将所有函数定义在一个文件中，减少模块导入。
"""

import subprocess  # 用于执行系统命令
import time  # 用于延迟
from ldap3 import Server, Connection, ALL, SUBTREE  # 导入ldap3模块


# 定义连接域服务器的函数
def connect_to_ad():    # 创建连接，批量登录server_list中的域服务器列表作
    # 定义空列表，用来存储所有域服务器的连接信息
    conn_list = []
    for server_list in ad_servers:
        try:
            server = Server(server_list, port=636, use_ssl=True, get_info=ALL, connect_timeout=2)
            conn = Connection(server, user=r'snimay\20240519', password='Snimay#!2024519', auto_bind=True)  # 设置管理员账号和密码,auto_bind=True表示自动绑定连接。
            # 返回连接信息和域服务器名称
            conn_list.append((conn, server_list))
        except Exception as e:
            # 捕获异常,继续执行下一个服务器的连接
            print(f"连接 {server_list} 失败，原因：{e}")
            continue
    return conn_list


# 主函数，询问和等待用户选择
def main_select():
    while True:
        computer_name = input('请输入要修改的计算机名称（s跳过）： ').strip()  # .strip()用于去除输入的空格

        if computer_name == '':  # 如果输入为空，则一直循环输入
            pass  # pass语句什么都不做，继续循环输入

        elif computer_name == 's':  # 如果输入s，则不修改计算机名，直接执行get_computer_info函数
            computer_operation(curr_computer_name)  # 不修改计算机名调用get_computer_info函数，

        else:  # 如果输入其它内容，则执行get_computer_info函数
            computer_operation(computer_name)


# 定义获取计算机描述信息的函数
def get_computer_description(computer_name):
    computer_dn = []   # 定义一个空列表，用于存储搜索到的计算机的DN
    for conn, server_list in conn_list:  # 遍历所有域服务器列表，即会修改列表中的所有域服务器的计算机密码。
        conn.search(search_base=base_dn, search_filter=f"(&(objectClass=computer)(cn={computer_name}))", search_scope=SUBTREE, attributes=['description'])

        if len(conn.entries) > 0:  # 如果搜索结果长度大于0，则证明计算机存在。
            computer_dn.append(conn.entries[0].description)  # 将计算机的DN添加到列表中

        else:
            return None

    # 只返回计算机的描述信息，不返回DN。
    return computer_dn[0]


# 定义获取计算机DN信息的函数
def get_computer_dn(computer_name):
    filter_str = f"(&(objectClass=computer)(cn={computer_name}))"
    return search_entry(filter_str)


# 定义用于删除计算机的函数
def delete_computer(computer_name):
    computer_dn = get_computer_dn(computer_name)  # 调用函数获取计算机DN信息。
    # print(computer_dn)

    for conn, server_list in conn_list:  # 遍历所有域服务器列表，即会修改列表中的所有域服务器的计算机密码。
        # 如果计算机不存在，则提示并返回。
        if computer_dn is None:
            print(f"找不到 {computer_name} 计算机。")
            conn.unbind()
            return

        if computer_dn:
            conn.delete(computer_dn)  # 根据计算机名获取计算机的dn，并删除计算机。
            if conn.result.get('description') == 'success':  # 判断是否删除成功。
                print(f'{server_list} 域服务器，计算机 {computer_name} 删除成功！')
                # return True  # 返回信息，告知其他程序删除成功。
            else:
                print(f'{server_list} 域服务器，计算机 {computer_name} 删除失败。 {conn.result}')
                # return False  # 返回信息，告知其他程序删除失败。
        conn.unbind()  # 关闭连接。
    join_ad(computer_name)  # 删除计算机成功后调用加域函数


# 定义用于搜索计算机DN信息的函数模板，返回搜索到的计算机的DN
def search_entry(filter_str):
    results = []  # 创建一个列表来存储所有的结果
    for conn, server_list in conn_list:  # 遍历所有域服务器列表
        conn.search(search_base=base_dn, search_filter=filter_str, search_scope=SUBTREE, attributes=['distinguishedName'])
        # print(server_list, len(conn.entries))
        if len(conn.entries) > 0:    # 如果找到了结果
            dn_value = conn.entries[0].distinguishedName.value  # 获取DN值
            # print(f"{dn_value} on {server_list}")  # 打印所有服务器找到的DN
            results.append((server_list, dn_value))  # 将结果添加到列表中
        else:  # 如果没有找到结果
            print(f"Dn not found on {server_list}")  # 打印没有找到结果的服务器

    return results[0][1] if results else None


# 该函数主要用于查找域服务器是否已存在计算机信息，如果存在则询问是否删除，只有删除了才能进行加域操作
def computer_operation(computer_name):
    computer_dn = get_computer_dn(computer_name)  # 获取计算机的DN
    computer_description = get_computer_description(computer_name)  # 获取计算机的描述信息

    if computer_dn is not None:  # 判断如果找到计算机，打印信息并询问是否删除
        print(f'搜索到域服务器已存在计算机 {computer_name} ：\n    最后一次登录：{computer_description} \n    目前存放路径：{computer_dn}\n')
        while True:  # 创建一个无限循环，直到得到有效输入y或n
            action = input(f'是否删除 {computer_name} ？ (y/n)： ').strip().lower()  # 询问是否删除，strip()去除空格，lower()将输入内容，都转为小写
            if action == 'y':  # 如果输入y，执行删除，
                delete_computer(computer_name)  # 调用删除函数
            elif action == 'n':  # 如果输入n，则返回重新输入计算机名搜索
                return  # 返回select_action函数，重新输入计算机名搜索
            else:  # 如果输入其它内容
                pass  # 什么都不做，继续循环输入
    else:  # 如果未找到，则使用当前用户输入的计算机名加域
        while True:  # 再创个无限循环，和前面效果一样，直到得到有效输入y或n
            action = input(f'是否使用 {computer_name} 计算机加入域？(y/n)： ').strip().lower()
            if action == 'y':
                join_ad(computer_name)  # 调用加域函数
                break
            elif action == 'n':
                return
            else:
                pass
        return


# 加域函数，通过调用PowerShell命令，将当前计算机加入域
def join_ad(computer_name):
    print(f'正在使用 {computer_name} 计算机名加域......')

    ''' 使用subprocess运行PowerShell命令操作加域 '''
    # 定义域名、用户名和密码
    domain = "snimay.com"
    username = "20240519"
    password = "Snimay#!2024519"
    # 构建PowerShell命令，加域关键命令

    if computer_name != curr_computer_name:  # 如果当前计算机名与输入的计算机名不同，则修改计算机名后加入域
        powershell_join_ad = f"""
        $domain = "{domain}"
        $username = "{username}"
        $password = ConvertTo-SecureString "{password}" -AsPlainText -Force
        Add-Computer -DomainName $domain -Credential (New-Object System.Management.Automation.PSCredential ($username, $password)) -NewName {computer_name} -Force
        """
    else:  # 如果当前计算机名与输入的计算机名相同，则不修改计算机名直接加入
        powershell_join_ad = f"""
        $domain = "{domain}"
        $username = "{username}"
        $password = ConvertTo-SecureString "{password}" -AsPlainText -Force
        Add-Computer -DomainName $domain -Credential (New-Object System.Management.Automation.PSCredential ($username, $password)) -Force
        """

    # 使用subprocess运行PowerShell加域命令
    result = subprocess.run(["powershell", "-Command", powershell_join_ad])

    # 下面增加判断subprocess.run的结果，如果失败则打印失败信息并且重新调用函数
    if result.returncode == 0:
        print(f'{computer_name} 计算机加域成功！')
        while True:
            action = input('是否重启计算机？(y/n)： ').strip().lower()
            if action == 'y':
                subprocess.run('shutdown -r -t 0', shell=True)  # 重启计算机，shell=True的作用是让命令在cmd中运行
                break  # 退出循环，并结束程序
            elif action == 'n':
                print('正在退出程序......')
                time.sleep(3)
                break
            else:
                pass
    else:  # 如果subprocess.run失败，打印失败信息并重新调用函数
        print(f'{computer_name} 计算机加域失败，请重试！')
        time.sleep(3)  # 延迟3秒后重新调用函数
        main_select()  # 返回重新输入计算机名搜索


if __name__ == '__main__':
    # 定义多个域服务器，存放在列表中
    ad_servers = ['192.168.41.50', '192.168.45.50', '192.168.84.50', '192.168.71.50']
    base_dn = 'DC=snimay,DC=com'  # 设置搜索的根节点
    conn_list = connect_to_ad()  # 连接所有域服务器

    # 获取当前系统的计算机名，将计算机名赋予给curr_computer_name变量，方便其它函数使用
    curr_computer_name = subprocess.check_output('hostname', shell=True).decode().strip()
    print("当前计算机名：", curr_computer_name)  # 打印当前计算机名

    # 调用主函数，会先让用输入要加域的计算机名
    main_select()
