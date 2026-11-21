#include <Servo.h>
//Autor: Amarildo Ferreira Oliveira
Servo garra;

const int PINO_SERVO = 9;
const int PINO_JOY_RX = A5;
const int PINO_JOY_RY = A4;

// Ângulos calibrados da garra
const int ANGULO_ABERTA = 30;
const int ANGULO_FECHADA = 180;
const int ANGULO_CENTRO = 80;

// Faixa central do joystick analógico (0 a 1023; centro fica perto de 512)
const int LIMITE_MIN = 300;
const int LIMITE_MAX = 700;

// Estados possíveis: "FECHADA", "ABERTA", "CENTRALIZADA"
String estadoAtual = "FECHADA";

bool travadoX = false;
bool travadoY = false;

void executarComando(char cmd) {
  cmd = toupper(cmd);

  if (cmd == 'A') {
    if (estadoAtual == "FECHADA" || estadoAtual == "CENTRALIZADA") {
      garra.write(ANGULO_ABERTA);
      estadoAtual = "ABERTA";
      Serial.println("OK: Garra ABERTA");
    } else {
      Serial.println("IGNORADO: Garra ja esta ABERTA");
    }
  }
  else if (cmd == 'F') {
    if (estadoAtual == "ABERTA" || estadoAtual == "CENTRALIZADA") {
      garra.write(ANGULO_FECHADA);
      estadoAtual = "FECHADA";
      Serial.println("OK: Garra FECHADA");
    } else {
      Serial.println("IGNORADO: Garra ja esta FECHADA");
    }
  }
  else if (cmd == 'C') {
    garra.write(ANGULO_CENTRO);
    estadoAtual = "CENTRALIZADA";
    Serial.println("OK: Garra CENTRALIZADA");
  }
}

void lerJoystick() {
  int valorX = analogRead(PINO_JOY_RX);
  int valorY = analogRead(PINO_JOY_RY);

  // Controle Abrir / Fechar pelo eixo RX (A5)
  if (!travadoX) {
    if (valorX < LIMITE_MIN) {
      executarComando('A');
      travadoX = true;
    } else if (valorX > LIMITE_MAX) {
      executarComando('F');
      travadoX = true;
    }
  } else if (valorX >= LIMITE_MIN && valorX <= LIMITE_MAX) {
    travadoX = false;
  }

  // Controle Centralizar pelo eixo RY (A4)
  if (!travadoY) {
    if (valorY < LIMITE_MIN || valorY > LIMITE_MAX) {
      executarComando('C');
      travadoY = true;
    }
  } else if (valorY >= LIMITE_MIN && valorY <= LIMITE_MAX) {
    travadoY = false;
  }
}

void setup() {
  Serial.begin(9600);
  garra.attach(PINO_SERVO);
  garra.write(ANGULO_FECHADA);
  Serial.println("Garra pronta. Estado inicial: FECHADA");
}

void loop() {
  lerJoystick();

  if (Serial.available() > 0) {
    char cmd = Serial.read();
    if (cmd != '\n' && cmd != '\r') {
      executarComando(cmd);
    }
  }
}
