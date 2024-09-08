import paramiko
import telnetlib
import schedule
import time
import logging
from concurrent.futures import ThreadPoolExecutor

# 配置日志记录
logging.basicConfig(
    filename='autosave.log',  # 指定日志文件名
    filemode='w',  # 文件模式：'a' 表示追加模式，'w' 表示覆盖模式
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)
logger = logging.getLogger(__name__)


# SSH 连接
def ssh_connect(host, username, password):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=username, password=password, timeout=10)

        # 发送保存命令
        logger.info(f"SSH: 向 {host} 发送 'save force' 命令")
        stdin, stdout, stderr = client.exec_command('save force')
        logger.info(f"SSH 输出来自 {host}: {stdout.read().decode()}")
        client.close()
        return True
    except Exception as e:
        logger.error(f"SSH 连接失败 {host}: {e}")
        return False


# Telnet 连接
def telnet_connect(host, username, password):
    try:
        tn = telnetlib.Telnet(host)
        # 读取提示信息，检查是否包含 "Username:" 或 "Login:"
        login_prompt = tn.read_until(b"Username:", timeout=10)
        if b"Username:" not in login_prompt:
            login_prompt = tn.read_until(b"Login:", timeout=10)
        tn.write(username.encode('ascii') + b"\n")
        tn.read_until(b"Password:", timeout=10)
        tn.write(password.encode('ascii') + b"\n")
        time.sleep(2)  # 等待登录完成

        logger.info(f"Telnet: 向 {host} 发送 'save force' 命令")
        tn.write(b"save force\n")
        tn.read_until(b"Configuration saved", timeout=10)
        output = tn.read_all().decode('ascii')
        logger.info(f"Telnet 输出来自 {host}: {output}")
        tn.close()
    except Exception as e:
        logger.error(f"Telnet 连接失败 {host}: {e}")


# 处理每个设备的函数，尝试两组用户名和密码
def process_device(host):
    logger.info(f"开始处理设备: {host}")
    credentials = [
        ('lpssy', 'lpssy123'),
        ('netconf', 'Lpssy@2024')
    ]

    success = False
    for username, password in credentials:
        logger.info(f"尝试使用用户名: {username} 连接 {host}")
        success = ssh_connect(host, username, password)
        if success:
            break
        else:
            logger.info(f"SSH 失败，切换到 Telnet...")

        success = telnet_connect(host, username, password)
        if success:
            break

    if not success:
        logger.error(f"{host} 无法通过 SSH 或 Telnet 连接")


# 生成 IP 地址范围
def generate_ip_ranges():
    ip_ranges = []
    for i in range(1, 255):
        ip_ranges.append(f"192.168.253.{i}")
        ip_ranges.append(f"192.168.254.{i}")
        ip_ranges.append(f"172.16.20.{i}")
    return ip_ranges


# 主要函数，处理所有设备
def run_save_command():
    hosts = generate_ip_ranges()

    with ThreadPoolExecutor(max_workers=100) as executor:
        for host in hosts:
            executor.submit(process_device, host)


# 定时任务
schedule.every().day.at("12:00").do(run_save_command)
schedule.every().day.at("18:00").do(run_save_command)

# 保持脚本运行
if __name__ == '__main__':
    logger.info("开始执行定时任务...")
    run_save_command()  # 立即执行一次
    while True:
        schedule.run_pending()
        time.sleep(1)
