#Autor: Amarildo Ferreira Oliveira
#Para o dia da apresentação
#Se aqui não funcionar abra o app na pasta
#G:\Meu Drive\Aula\Programação\Exercícios para praticar
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
import cv2
import mediapipe as mp
import serial

# Substitua pela porta real do seu Arduino (ex: COM3, COM4, COM5 ou /dev/ttyUSB0)
PORTA_SERIAL = 'COM5'
VELOCIDADE = 9600

conexao = None
conectado = False
camera_ativa = False
cap = None

# Estados possíveis: "FECHADA", "ABERTA", "CENTRALIZADA"
estado_garra = 'FECHADA'
trava_estado = threading.Lock()


def registrar_log(mensagem):
  def _inserir():
    txt_log.insert(tk.END, f'{mensagem}\n')
    txt_log.see(tk.END)

  root.after(0, _inserir)


def conectar_arduino():
  global conexao, conectado
  try:
    conexao = serial.Serial(PORTA_SERIAL, VELOCIDADE, timeout=0.1)
    time.sleep(2)
    conectado = True
    lbl_status.config(text='Status: Conectado 🟢', foreground='green')
    btn_conectar.config(state='disabled')
    threading.Thread(target=ler_serial_arduino, daemon=True).start()
  except Exception as e:
    messagebox.showerror(
        'Erro de Conexão',
        f'Não foi possível conectar na porta {PORTA_SERIAL}.\nErro: {e}',
    )


def enviar(comando, silencioso_se_ignorado=False):
  global estado_garra
  if not conectado or not conexao:
    return False

  cmd = comando.strip().upper()
  if not cmd:
    return False
  cmd = cmd[0]

  with trava_estado:
    if cmd == 'A':
      if estado_garra not in ('FECHADA', 'CENTRALIZADA'):
        if not silencioso_se_ignorado:
          registrar_log(
              f'Aguardando fechar: garra já está {estado_garra}.'
          )
        return False
      novo_estado = 'ABERTA'
    elif cmd == 'F':
      if estado_garra not in ('ABERTA', 'CENTRALIZADA'):
        if not silencioso_se_ignorado:
          registrar_log(
              f'Aguardando abrir: garra já está {estado_garra}.'
          )
        return False
      novo_estado = 'FECHADA'
    elif cmd == 'C':
      novo_estado = 'CENTRALIZADA'
    else:
      novo_estado = estado_garra

    try:
      conexao.write(cmd.encode('utf-8'))
      estado_garra = novo_estado
      return True
    except Exception as e:
      registrar_log(f'Erro ao enviar: {e}')
      return False


def enviar_texto_livre(event=None):
  texto = txt_comando.get().strip().upper()
  if texto:
    enviar(texto[0])
    txt_comando.delete(0, tk.END)


def ler_serial_arduino():
  while conectado:
    try:
      if conexao and conexao.in_waiting > 0:
        linha = conexao.readline().decode('utf-8', errors='ignore').strip()
        if linha:
          registrar_log(f'Arduino: {linha}')
    except Exception:
      break


def alternar_visao_computacional():
  global camera_ativa

  if not conectado:
    messagebox.showwarning(
        'Aviso', 'Conecte o Arduino antes de iniciar a câmera!'
    )
    return

  if camera_ativa:
    camera_ativa = False
    btn_visao.config(text='⏳ Parando câmera...', state='disabled')
    return

  if not hasattr(mp, 'solutions') or not hasattr(mp.solutions, 'hands'):
    messagebox.showerror(
        'Erro MediaPipe',
        'O módulo mp.solutions.hands não foi encontrado neste ambiente.\n'
        'Verifique a versão do mediapipe instalada (ex: pip install'
        ' mediapipe==0.10.14).',
    )
    return

  camera_ativa = True
  btn_visao.config(
      text='🛑 Parar Visão Computacional', bg='#ffcccc', state='normal'
  )

  def rodar_ia():
    global camera_ativa, cap
    cap = cv2.VideoCapture(0)

    if not cap or not cap.isOpened():
      registrar_log('Erro: Não foi possível abrir a câmera (índice 0).')
      camera_ativa = False
      root.after(
          0,
          lambda: btn_visao.config(
              text='🎥 Iniciar Visão Computacional (Mão)',
              bg='#f0f0f0',
              state='normal',
          ),
      )
      return

    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5,
    )

    try:
      while camera_ativa:
        success, img = cap.read()
        if not success or img is None:
          registrar_log('Aviso: Falha ao ler quadro da câmera.')
          break

        img = cv2.flip(img, 1)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(img_rgb)

        if results.multi_hand_landmarks:
          for hand_lms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
            lms = hand_lms.landmark

            dedos_levantados = 0
            # Indicador (8 acima de 6), Médio (12 acima de 10),
            # Anelar (16 acima de 14), Mindinho (20 acima de 18)
            if lms[8].y < lms[6].y:
              dedos_levantados += 1
            if lms[12].y < lms[10].y:
              dedos_levantados += 1
            if lms[16].y < lms[14].y:
              dedos_levantados += 1
            if lms[20].y < lms[18].y:
              dedos_levantados += 1

            cv2.putText(
                img,
                f'Dedos: {dedos_levantados}',
                (30, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2,
            )

            # Mão aberta (3 ou mais dedos): abre se estiver FECHADA ou CENTRALIZADA
            if dedos_levantados >= 3:
              if estado_garra in ('FECHADA', 'CENTRALIZADA'):
                if enviar('A', silencioso_se_ignorado=True):
                  registrar_log(
                      'Mão aberta -> Garra ABERTA (aguardando fechar)'
                  )
              cv2.putText(
                  img,
                  f'GARRA: {estado_garra}',
                  (30, 50),
                  cv2.FONT_HERSHEY_SIMPLEX,
                  1,
                  (0, 255, 0),
                  2,
              )
            # Mão fechada (menos de 3 dedos): fecha se estiver ABERTA ou CENTRALIZADA
            else:
              if estado_garra in ('ABERTA', 'CENTRALIZADA'):
                if enviar('F', silencioso_se_ignorado=True):
                  registrar_log(
                      'Mão fechada -> Garra FECHADA (aguardando abrir)'
                  )
              cv2.putText(
                  img,
                  f'GARRA: {estado_garra}',
                  (30, 50),
                  cv2.FONT_HERSHEY_SIMPLEX,
                  1,
                  (0, 0, 255),
                  2,
              )
        else:
          cv2.putText(
              img,
              f'Mão não detectada | Garra: {estado_garra}',
              (30, 50),
              cv2.FONT_HERSHEY_SIMPLEX,
              0.8,
              (200, 200, 200),
              2,
          )

        cv2.imshow(
            'Controle por Visão Computacional - Pressione ESC para sair', img
        )

        if cv2.waitKey(1) & 0xFF == 27:
          camera_ativa = False
          break
    finally:
      hands.close()
      if cap:
        cap.release()
        cap = None
      cv2.destroyAllWindows()
      camera_ativa = False
      root.after(
          0,
          lambda: btn_visao.config(
              text='🎥 Iniciar Visão Computacional (Mão)',
              bg='#f0f0f0',
              state='normal',
          ),
      )

  threading.Thread(target=rodar_ia, daemon=True).start()


def ao_fechar():
  global camera_ativa, conectado, conexao
  camera_ativa = False
  conectado = False
  time.sleep(0.2)
  if cap and cap.isOpened():
    cap.release()
  cv2.destroyAllWindows()
  if conexao and conexao.is_open:
    try:
      conexao.close()
    except Exception:
      pass
  root.destroy()


# --- INTERFACE TKINTER ---
root = tk.Tk()
root.title('Controle da Garra Robótica - Arduino & Python & IA')
root.geometry('400x590')
root.resizable(False, False)
root.protocol('WM_DELETE_WINDOW', ao_fechar)

estilo = ttk.Style()
estilo.theme_use('clam')

# Título Principal
lbl_titulo = tk.Label(
    root, text='Controle da Garra Robótica', font=('Arial', 14, 'bold')
)
lbl_titulo.pack(pady=(10, 2))

# Subtítulo (Logo abaixo do título)
lbl_subtitulo = tk.Label(
    root,
    text='Especialização em Ensino de Ciências e Matemática - IFMS',
    font=('Arial', 9, 'italic'),
    foreground='#555555',
)
lbl_subtitulo.pack(pady=(0, 10))

lbl_status = tk.Label(
    root, text='Status: Desconectado 🔴', font=('Arial', 10), foreground='red'
)
lbl_status.pack(pady=2)

btn_conectar = ttk.Button(
    root, text='Conectar ao Arduino', command=conectar_arduino
)
btn_conectar.pack(pady=4)

frame_botoes = ttk.LabelFrame(root, text=' Comandos por Botão ')
frame_botoes.pack(fill='both', expand='yes', padx=15, pady=6)

btn_abrir = ttk.Button(
    frame_botoes, text='🔓 Abrir Garra (A)', command=lambda: enviar('A')
)
btn_abrir.pack(fill='x', padx=20, pady=4)

btn_centralizar = ttk.Button(
    frame_botoes,
    text='🎯 Centralizar / Meio (C)',
    command=lambda: enviar('C'),
)
btn_centralizar.pack(fill='x', padx=20, pady=4)

btn_fechar = ttk.Button(
    frame_botoes, text='🔒 Fechar Garra (F)', command=lambda: enviar('F')
)
btn_fechar.pack(fill='x', padx=20, pady=4)

btn_visao = tk.Button(
    root,
    text='🎥 Iniciar Visão Computacional (Mão)',
    command=alternar_visao_computacional,
    font=('Arial', 10),
    bg='#f0f0f0',
    relief='raised',
    cursor='hand2',
)
btn_visao.pack(fill='x', padx=15, pady=6, ipady=3)

frame_digitar = ttk.LabelFrame(root, text=' Digitar Comando (Letra) ')
frame_digitar.pack(fill='both', expand='yes', padx=15, pady=4)

txt_comando = ttk.Entry(frame_digitar, font=('Arial', 11))
txt_comando.pack(side='left', fill='x', expand=True, padx=10, pady=6)
txt_comando.bind('<Return>', enviar_texto_livre)

btn_enviar = ttk.Button(
    frame_digitar, text='Enviar', command=enviar_texto_livre
)
btn_enviar.pack(side='right', padx=10, pady=6)

frame_log = ttk.LabelFrame(root, text=' Log de Resposta ')
frame_log.pack(fill='both', expand='yes', padx=15, pady=6)

txt_log = tk.Text(frame_log, height=3, font=('Consolas', 9))
txt_log.pack(fill='both', expand=True, padx=5, pady=4)

root.mainloop()