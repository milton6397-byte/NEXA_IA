
# NEXA IA
# Assistente local criada por Milton Cesar Martins
# Interface em Kivy + modelo local Qwen via llamafile

import json
import threading
import urllib.request
import urllib.error

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


# ==========================================================
# 1. CONFIGURAÇÃO
# ==========================================================

API_URL = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "Qwen3-0.6B-Q8_0.gguf"

Window.size = (420, 680)
Window.minimum_width = 320
Window.minimum_height = 450


# ==========================================================
# 2. IDENTIDADE DA NEXA
# Para mudar a identidade no futuro, altere somente este texto.
# ==========================================================

IDENTIDADE_NEXA = """
Você é a NEXA IA, uma assistente de inteligência artificial local,
criada por Milton Cesar Martins.

SUA IDENTIDADE:
- Seu nome é NEXA IA.
- Seu criador é Milton Cesar Martins.
- Você conversa em português brasileiro.
- Você é uma assistente digital, não uma pessoa humana.
- Você deve manter uma comunicação natural, respeitosa,
  acolhedora e direta.

SUA FINALIDADE:
- Ajudar seu criador a estudar programação e tecnologia.
- Auxiliar em projetos de inteligência artificial.
- Explicar Python, SQL, Linux e conceitos de informática.
- Ajudar a planejar projetos de software e hardware.
- Conversar e responder perguntas com clareza.

SEU COMPORTAMENTO:
- Responda primeiro ao que foi perguntado.
- Prefira explicações simples e práticas.
- Quando houver várias etapas, apresente uma etapa de cada vez.
- Não invente informações quando não souber a resposta.
- Não afirme que possui recursos que ainda não foram implementados.
- Considere o histórico da conversa ao formular suas respostas.
- Se perguntarem quem você é, diga que é a NEXA IA,
  uma assistente local criada por Milton Cesar Martins.
- Se perguntarem para que você serve, explique sua finalidade
  de maneira simples e objetiva.

Esta identidade orienta suas respostas, mas suas capacidades reais
dependem do modelo local e das funções implementadas no programa.
"""


# ==========================================================
# 3. APLICAÇÃO
# ==========================================================

class NEXAApp(App):

    def build(self):
        self.title = "NEXA IA"
        self.history = []
        self.busy = False

        Window.clearcolor = (0.055, 0.065, 0.09, 1)

        root = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )

        # Cabeçalho
        header = Label(
            text="[b]NEXA IA[/b]\n"
                 "[color=91B9FF]Assistente local[/color]",
            markup=True,
            font_size="22sp",
            size_hint_y=None,
            height=dp(65),
            halign="center",
            valign="middle"
        )
        root.add_widget(header)

        # Área de conversa
        self.scroll = ScrollView(
            do_scroll_x=False,
            bar_width=dp(4)
        )

        self.messages = BoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=[dp(5), dp(8), dp(5), dp(8)],
            size_hint_y=None
        )

        self.messages.bind(
            minimum_height=self.messages.setter("height")
        )

        self.scroll.add_widget(self.messages)
        root.add_widget(self.scroll)

        # Área de digitação
        input_row = BoxLayout(
            orientation="horizontal",
            spacing=dp(6),
            size_hint_y=None,
            height=dp(50)
        )

        self.input_box = TextInput(
            hint_text="Digite sua mensagem...",
            multiline=False,
            font_size="16sp",
            size_hint_x=0.78
        )

        self.input_box.bind(
            on_text_validate=lambda *_: self.send_message()
        )

        self.send_button = Button(
            text="Enviar",
            size_hint_x=0.22,
            font_size="15sp"
        )

        self.send_button.bind(
            on_release=lambda *_: self.send_message()
        )

        input_row.add_widget(self.input_box)
        input_row.add_widget(self.send_button)
        root.add_widget(input_row)

        self.add_message(
            "NEXA",
            "Olá! Eu sou a NEXA IA. Como posso ajudar?"
        )

        return root

    # ======================================================
    # 4. MOSTRAR MENSAGENS
    # ======================================================

    def add_message(self, sender, text):
        label = Label(
            text=f"[b]{sender}[/b]\n{text}",
            markup=True,
            font_size="15sp",
            halign="left",
            valign="top",
            size_hint_y=None,
            color=(0.92, 0.94, 1, 1)
        )

        label.bind(
            width=lambda widget, width:
                setattr(widget, "text_size", (max(1, width - dp(12)), None))
        )

        label.bind(
            texture_size=lambda widget, size:
                setattr(widget, "height", size[1] + dp(16))
        )

        self.messages.add_widget(label)

        Clock.schedule_once(
            lambda dt: setattr(self.scroll, "scroll_y", 0),
            0.1
        )

    # ======================================================
    # 5. ENVIAR MENSAGEM
    # ======================================================

    def send_message(self):
        if self.busy:
            return

        question = self.input_box.text.strip()

        if not question:
            return

        self.input_box.text = ""
        self.busy = True

        self.input_box.disabled = True
        self.send_button.disabled = True
        self.send_button.text = "..."

        self.add_message("Você", question)

        # O marcador /no_think evita respostas de raciocínio
        # interno em modelos Qwen compatíveis com esse recurso.
        self.history.append({
            "role": "user",
            "content": "/no_think " + question
        })

        # Faz uma cópia do histórico para esta solicitação.
        history_snapshot = list(self.history)

        threading.Thread(
            target=self.ask_model,
            args=(history_snapshot,),
            daemon=True
        ).start()

    # ======================================================
    # 6. CONVERSAR COM O QWEN LOCAL
    # ======================================================

    def ask_model(self, history_snapshot):
        answer = None
        error_message = None

        messages = [
            {
                "role": "system",
                "content": IDENTIDADE_NEXA
            }
        ] + history_snapshot

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 256,
            "chat_template_kwargs": {
                "enable_thinking": False
            }
        }

        try:
            data = json.dumps(payload).encode("utf-8")

            request = urllib.request.Request(
                API_URL,
                data=data,
                headers={
                    "Content-Type": "application/json"
                },
                method="POST"
            )

            with urllib.request.urlopen(
                request,
                timeout=120
            ) as response:
                result = json.loads(
                    response.read().decode("utf-8")
                )

            answer = result["choices"][0]["message"]["content"]

            if not answer or not answer.strip():
                answer = "Não consegui formular uma resposta. Tente novamente."

        except urllib.error.URLError:
            error_message = (
                "Não consegui conectar ao Qwen. "
                "Verifique se o servidor llamafile está aberto "
                "e funcionando na porta 8080."
            )

        except (KeyError, IndexError, ValueError):
            error_message = (
                "Recebi uma resposta em formato inesperado do modelo."
            )

        except Exception as error:
            error_message = (
                f"Ocorreu um erro: {type(error).__name__}: {error}"
            )

        Clock.schedule_once(
            lambda dt: self.finish_reply(answer, error_message),
            0
        )

    # ======================================================
    # 7. FINALIZAR RESPOSTA
    # ======================================================

    def finish_reply(self, answer, error_message):
        if error_message:
            self.add_message("NEXA", error_message)

            # Remove a última pergunta do histórico se houve erro.
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()

        else:
            self.history.append({
                "role": "assistant",
                "content": answer
            })

            self.add_message("NEXA", answer)

        self.busy = False
        self.input_box.disabled = False
        self.send_button.disabled = False
        self.send_button.text = "Enviar"
        self.input_box.focus = True


# ==========================================================
# 8. INICIAR A NEXA
# ==========================================================

if __name__ == "__main__":
    NEXAApp().run()
