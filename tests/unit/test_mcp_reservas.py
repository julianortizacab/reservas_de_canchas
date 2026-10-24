import asyncio
from contextlib import contextmanager
from datetime import date, datetime

from fastmcp import Client

from flaskr.infrastructure.adaptadorEntrada.reservaMcpServer import crear_servidor_mcp


def servidor(servicio):
    @contextmanager
    def proveedor():
        yield servicio

    return crear_servidor_mcp(proveedor)


def test_servidor_publica_tools_resources_y_prompt(servicio):
    mcp = servidor(servicio)
    servicio.crear_reserva(
        1,
        1,
        datetime(2030, 1, 16, 10),
        datetime(2030, 1, 16, 11),
    )

    async def consultar():
        async with Client(mcp) as client:
            tool_specs = await client.list_tools()
            tools = {tool.name for tool in tool_specs}
            resources = {str(resource.uri) for resource in await client.list_resources()}
            templates = {
                template.uriTemplate for template in await client.list_resource_templates()
            }
            prompts = {prompt.name for prompt in await client.list_prompts()}
            catalogo = await client.read_resource("canchas://catalogo")
            reserva = await client.read_resource("reservas://1")
            prompt = await client.get_prompt(
                "agendar_cancha",
                {"deporte": "futbol", "fecha": date(2030, 1, 16).isoformat()},
            )
            return tool_specs, tools, resources, templates, prompts, catalogo, reserva, prompt

    tool_specs, tools, resources, templates, prompts, catalogo, reserva, prompt = asyncio.run(
        consultar()
    )
    assert {
        "listar_canchas",
        "buscar_cliente",
        "consultar_disponibilidad",
        "sugerir_horarios",
        "cotizar_reserva",
        "listar_reservas",
        "obtener_reserva",
        "crear_reserva",
        "confirmar_reserva",
        "cancelar_reserva",
        "completar_reserva",
    } <= tools
    assert "canchas://catalogo" in resources
    assert "reservas://{reserva_id}" in templates
    assert "agendar_cancha" in prompts
    annotations = {tool.name: tool.annotations for tool in tool_specs}
    assert annotations["listar_canchas"].readOnlyHint
    assert annotations["cancelar_reserva"].destructiveHint
    assert "Fútbol 1" in catalogo[0].text
    assert '"id": 1' in reserva[0].text
    assert "solicita confirmación explícita" in prompt.messages[0].content.text


def test_tools_de_busqueda_cotizacion_y_creacion(servicio):
    mcp = servidor(servicio)

    async def ejecutar():
        async with Client(mcp) as client:
            canchas = await client.call_tool("listar_canchas", {"deporte": "padel"})
            clientes = await client.call_tool("buscar_cliente", {"texto": "Ana"})
            cotizacion = await client.call_tool(
                "cotizar_reserva",
                {
                    "cancha_id": 1,
                    "inicio": datetime(2030, 1, 16, 10).isoformat(),
                    "fin": datetime(2030, 1, 16, 12).isoformat(),
                },
            )
            reserva = await client.call_tool(
                "crear_reserva",
                {
                    "cancha_id": 1,
                    "cliente_id": 1,
                    "inicio": datetime(2030, 1, 16, 10).isoformat(),
                    "fin": datetime(2030, 1, 16, 12).isoformat(),
                },
            )
            return canchas, clientes, cotizacion, reserva

    canchas, clientes, cotizacion, reserva = asyncio.run(ejecutar())
    assert canchas.structured_content["result"][0]["deporte"] == "padel"
    assert clientes.structured_content["result"] == [{"id": 1, "nombre": "Ana"}]
    assert cotizacion.structured_content["total"] == 200.0
    assert reserva.structured_content["estado"] == "PENDIENTE"


def test_tool_devuelve_error_de_negocio_accionable(servicio):
    mcp = servidor(servicio)

    async def ejecutar():
        async with Client(mcp) as client:
            return await client.call_tool(
                "consultar_disponibilidad",
                {"cancha_id": 999, "fecha": date(2030, 1, 16).isoformat()},
                raise_on_error=False,
            )

    result = asyncio.run(ejecutar())
    assert result.is_error
    assert "no existe" in result.content[0].text


def test_sugerencias_devuelven_franjas_concretas(servicio):
    mcp = servidor(servicio)

    async def ejecutar():
        async with Client(mcp) as client:
            return await client.call_tool(
                "sugerir_horarios",
                {
                    "cancha_id": 1,
                    "fecha": date(2030, 1, 16).isoformat(),
                    "duracion_horas": 1,
                },
            )

    result = asyncio.run(ejecutar())
    assert len(result.structured_content["result"]) == 10
    assert result.structured_content["result"][0] == {
        "inicio": datetime(2030, 1, 16, 8).isoformat(),
        "fin": datetime(2030, 1, 16, 9).isoformat(),
    }
