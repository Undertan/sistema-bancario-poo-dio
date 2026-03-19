from abc import ABC, abstractmethod
from datetime import datetime
import textwrap
import json

# ====================== CLASSES (conforme UML) ======================

class Transacao(ABC):
    @property
    @abstractmethod
    def valor(self):
        pass

    @abstractmethod
    def registrar(self, conta):
        pass


class Saque(Transacao):
    def __init__(self, valor: float):
        self._valor = valor

    @property
    def valor(self):
        return self._valor

    def registrar(self, conta):
        sucesso = conta.sacar(self.valor)
        if sucesso:
            conta.historico.adicionar_transacao(self)


class Deposito(Transacao):
    def __init__(self, valor: float):
        self._valor = valor

    @property
    def valor(self):
        return self._valor

    def registrar(self, conta):
        sucesso = conta.depositar(self.valor)
        if sucesso:
            conta.historico.adicionar_transacao(self)


class Historico:
    def __init__(self):
        self._transacoes = []

    @property
    def transacoes(self):
        return self._transacoes

    def adicionar_transacao(self, transacao):
        self._transacoes.append({
            "tipo": transacao.__class__.__name__,
            "valor": transacao.valor,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })


class Cliente:
    def __init__(self, endereco: str):
        self.endereco = endereco
        self.contas = []

    def realizar_transacao(self, conta, transacao):
        transacao.registrar(conta)

    def adicionar_conta(self, conta):
        self.contas.append(conta)


class PessoaFisica(Cliente):
    def __init__(self, nome: str, data_nascimento: str, cpf: str, endereco: str):
        super().__init__(endereco)
        self.nome = nome
        self.data_nascimento = data_nascimento
        self.cpf = cpf

    def to_dict(self):
        return {
            "nome": self.nome,
            "data_nascimento": self.data_nascimento,
            "cpf": self.cpf,
            "endereco": self.endereco
        }


class Conta:
    def __init__(self, numero: int, cliente: Cliente):
        self._saldo = 0.0
        self._numero = numero
        self._agencia = "0001"
        self._cliente = cliente
        self._historico = Historico()

    @classmethod
    def nova_conta(cls, cliente: Cliente, numero: int):
        return cls(numero, cliente)

    @property
    def saldo(self): return self._saldo
    @property
    def numero(self): return self._numero
    @property
    def agencia(self): return self._agencia
    @property
    def cliente(self): return self._cliente
    @property
    def historico(self): return self._historico

    def depositar(self, valor: float) -> bool:
        if valor <= 0:
            print("\n@@@ Operação falhou! Valor inválido. @@@")
            return False
        self._saldo += valor
        print("\n=== Depósito realizado com sucesso! ===")
        return True

    def sacar(self, valor: float) -> bool:
        if valor > self._saldo:
            print("\n@@@ Operação falhou! Saldo insuficiente. @@@")
            return False
        elif valor <= 0:
            print("\n@@@ Operação falhou! Valor inválido. @@@")
            return False
        self._saldo -= valor
        print("\n=== Saque realizado com sucesso! ===")
        return True


class ContaCorrente(Conta):
    def __init__(self, numero: int, cliente: Cliente, limite: float = 500, limite_saques: int = 3):
        super().__init__(numero, cliente)
        self.limite = limite
        self.limite_saques = limite_saques

    def sacar(self, valor: float) -> bool:
        numero_saques = len([t for t in self.historico.transacoes if t["tipo"] == "Saque"])
        if valor > self.limite:
            print("\n@@@ Operação falhou! Valor excede o limite. @@@")
            return False
        if numero_saques >= self.limite_saques:
            print("\n@@@ Operação falhou! Limite de saques diários atingido. @@@")
            return False
        return super().sacar(valor)

    def __str__(self):
        return f"""\
            Agência:\t{self.agencia}
            C/C:\t\t{self.numero}
            Titular:\t{self.cliente.nome}
        """

    def to_dict(self):
        return {
            "numero": self.numero,
            "agencia": self.agencia,
            "saldo": self.saldo,
            "limite": self.limite,
            "limite_saques": self.limite_saques,
            "cpf_titular": self.cliente.cpf,
            "historico": self.historico.transacoes
        }


# ====================== SALVAMENTO AUTOMÁTICO ======================

def salvar_dados(clientes, contas):
    dados = {
        "clientes": [cliente.to_dict() for cliente in clientes],
        "contas": [conta.to_dict() for conta in contas]
    }
    with open("dados_bancarios.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)


def carregar_dados():
    try:
        with open("dados_bancarios.json", "r", encoding="utf-8") as f:
            dados = json.load(f)

        clientes = []
        contas = []
        cpf_to_cliente = {}

        for c_data in dados.get("clientes", []):
            cliente = PessoaFisica(
                c_data["nome"], c_data["data_nascimento"],
                c_data["cpf"], c_data["endereco"]
            )
            clientes.append(cliente)
            cpf_to_cliente[cliente.cpf] = cliente

        for c_data in dados.get("contas", []):
            cliente = cpf_to_cliente.get(c_data["cpf_titular"])
            if cliente:
                conta = ContaCorrente.nova_conta(cliente, c_data["numero"])
                conta._saldo = c_data["saldo"]
                conta.limite = c_data["limite"]
                conta.limite_saques = c_data["limite_saques"]
                conta.historico._transacoes = c_data.get("historico", [])
                contas.append(conta)
                cliente.adicionar_conta(conta)

        return clientes, contas
    except:
        return [], []


# ====================== FUNÇÕES DO MENU ======================

def menu():
    menu_texto = """\n
    ================ MENU ================
    [d] Depositar
    [s] Sacar
    [e] Extrato
    [nc] Nova conta
    [lc] Listar contas
    [nu] Novo usuário
    [q] Sair
    => """
    return input(textwrap.dedent(menu_texto))


def filtrar_cliente(cpf, clientes):
    return next((c for c in clientes if c.cpf == cpf), None)


def recuperar_conta_cliente(cliente):
    return cliente.contas[0] if cliente.contas else None


def depositar(clientes):
    cpf = input("\nInforme o CPF do titular: ")
    cliente = filtrar_cliente(cpf, clientes)
    if not cliente:
        print("\n@@@ Cliente não encontrado! @@@")
        return

    valor_str = input("Informe o valor do depósito: ").strip().replace(",", ".")
    try:
        valor = float(valor_str)
    except:
        print("\n@@@ Valor inválido! @@@")
        return

    transacao = Deposito(valor)
    conta = recuperar_conta_cliente(cliente)
    if conta:
        cliente.realizar_transacao(conta, transacao)


def sacar(clientes):
    cpf = input("\nInforme o CPF do titular: ")
    cliente = filtrar_cliente(cpf, clientes)
    if not cliente:
        print("\n@@@ Cliente não encontrado! @@@")
        return

    valor_str = input("Informe o valor do saque: ").strip().replace(",", ".")
    try:
        valor = float(valor_str)
    except:
        print("\n@@@ Valor inválido! @@@")
        return

    transacao = Saque(valor)
    conta = recuperar_conta_cliente(cliente)
    if conta:
        cliente.realizar_transacao(conta, transacao)


def exibir_extrato(clientes):
    cpf = input("\nInforme o CPF do titular: ")
    cliente = filtrar_cliente(cpf, clientes)
    if not cliente:
        print("\n@@@ Cliente não encontrado! @@@")
        return
    conta = recuperar_conta_cliente(cliente)
    if not conta:
        return

    print("\n================ EXTRATO ================")
    for t in conta.historico.transacoes:
        print(f"{t['data']} - {t['tipo']}: R$ {t['valor']:.2f}")
    print(f"\nSaldo atual: R$ {conta.saldo:.2f}")
    print("==========================================")


def criar_cliente(clientes):
    cpf = input("\nInforme o CPF: ")
    if filtrar_cliente(cpf, clientes):
        print("\n@@@ CPF já cadastrado! @@@")
        return
    nome = input("Nome completo: ")
    data_nascimento = input("Data de nascimento (dd-mm-aaaa): ")
    endereco = input("Endereço: ")

    cliente = PessoaFisica(nome, data_nascimento, cpf, endereco)
    clientes.append(cliente)
    print("\n=== Cliente criado com sucesso! ===")


def criar_conta(numero_conta, clientes, contas):
    cpf = input("\nInforme o CPF do titular: ")
    cliente = filtrar_cliente(cpf, clientes)
    if not cliente:
        print("\n@@@ Cliente não encontrado! @@@")
        return

    conta = ContaCorrente.nova_conta(cliente, numero_conta)
    contas.append(conta)
    cliente.adicionar_conta(conta)
    print(f"\n=== Conta {numero_conta} criada com sucesso! ===")


def listar_contas(contas):
    if not contas:
        print("\nNenhuma conta cadastrada.")
        return
    for conta in contas:
        print("=" * 100)
        print(textwrap.dedent(str(conta)))


# ====================== MAIN ======================

def main():
    clientes, contas = carregar_dados()
    print("✅ Dados carregados automaticamente!")

    while True:
        opcao = menu()

        if opcao == "d":
            depositar(clientes)
            salvar_dados(clientes, contas)
        elif opcao == "s":
            sacar(clientes)
            salvar_dados(clientes, contas)
        elif opcao == "e":
            exibir_extrato(clientes)
        elif opcao == "nu":
            criar_cliente(clientes)
            salvar_dados(clientes, contas)
        elif opcao == "nc":
            numero_conta = len(contas) + 1
            criar_conta(numero_conta, clientes, contas)
            salvar_dados(clientes, contas)
        elif opcao == "lc":
            listar_contas(contas)
        elif opcao == "q":
            salvar_dados(clientes, contas)
            print("\n💾 Dados salvos! Até logo!")
            break
        else:
            print("\n@@@ Operação inválida! @@@")


if __name__ == "__main__":
    main()