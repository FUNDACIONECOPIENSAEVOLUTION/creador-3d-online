# EcoBlend MCP Nube — prueba privada gratuita

**Estado:** implementación de laboratorio, no un servicio multiusuario de producción.
**Objetivo:** que una IA conectada a ChatGPT pueda inspeccionar y construir modelos en una pestaña de EcoBlend abierta desde cualquier computador sin instalar modelos de IA, Blender o Node.js en ese equipo.

El editor continúa alojado en GitHub Pages. Un Worker gratuito de Cloudflare, con Durable Objects, publica `/mcp` mediante HTTPS y ofrece un WebSocket seguro `/ws` con salas temporales. **El Worker no ejecuta renderizados ni genera automáticamente personajes hiperrealistas**: solo enruta operaciones validadas a la pestaña web y solicita aprobación del propietario.

## 1. Publicar el servidor (sin instalar Node en el computador)

Se necesita una cuenta **Cloudflare** con Workers habilitado. El plan Free actualmente permite Durable Objects con almacenamiento SQLite, sujeto a cuotas; comprueba los límites vigentes. No necesitas dominio propio.

1. Entra en https://dash.cloudflare.com y crea o utiliza una cuenta gratuita.
2. Obtén el **Account ID** en la cuenta Cloudflare.
3. Genera un API Token para el despliegue. En la creación inicial de un Worker nuevo, la documentación de Cloudflare requiere **Workers Admin** sobre el producto Workers de esa cuenta; para despliegues posteriores puedes sustituirlo por un token con **Editor** restringido a ese Worker. No uses la clave API global, no compartas tokens y revoca los permisos de creación que dejen de ser necesarios.
4. Genera una clave aleatoria privada de 32 bytes o más. Puedes hacerlo en PowerShell con:
   ```powershell
   ([guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
   ```
   Guárdala fuera de GitHub y de los chats. No se le envía a la IA.
5. En **GitHub → creador-3d-online → Settings → Secrets and variables → Actions**, crea estos tres *Repository secrets*:
   - `CLOUDFLARE_API_TOKEN` (token de despliegue Cloudflare).
   - `CLOUDFLARE_ACCOUNT_ID` (identificador de cuenta Cloudflare).
   - `ECOBLEND_PILOT_KEY` (clave privada generada en el paso 4).
6. En **GitHub → Actions → Desplegar EcoBlend MCP Nube → Run workflow**, ejecútalo una sola vez. El workflow instala las herramientas en el runner de GitHub, despliega el Worker y guarda la clave mediante `wrangler secret put`. No usa los recursos gráficos del PC.
7. Consulta el registro exitoso: Wrangler muestra una URL similar a `https://ecoblend-mcp-piloto.<tu-subdominio>.workers.dev`. **Esa URL es un ejemplo, no un dominio real garantizado.** Visita `URL/health`, que debe responder con JSON indicando el MCP en `/mcp`.

Si el despliegue falla, mira las líneas de error de la acción. Algunas cuentas podrían necesitar habilitar Durable Objects/Workers en Cloudflare. No publiquen credenciales en issues, commits ni mensajes de chat.

## 2. Abrir EcoBlend en una sesión privada

1. Abre https://fundacionecopiensaevolution.github.io/creador-3d-online/
2. En **MCP Nube · ChatGPT**, pega la URL base `https://…workers.dev` (sin `/mcp`).
3. Introduce temporalmente la misma `ECOBLEND_PILOT_KEY` guardada en GitHub. **No la pongas en el chat ni en una captura**. El navegador la transmite únicamente por HTTPS a `/pair`, no la guarda en localStorage y borra el campo después de usarla.
4. Pulsa **Conectar nube**. Recibirás un **identificador firmado de sala temporal de 20 minutos** (UUID, vencimiento y firma criptográfica). Si no aparece, revisa los mensajes del panel.
5. Deja abierta la pestaña EcoBlend. Cada acción de la IA pide una confirmación visible en esa misma pestaña; **incluso leer la escena o mostrar una imagen requiere aprobación**.
6. Para cancelar de inmediato, pulsa **Desconectar**. Tras 20 minutos reconecta.

El identificador de sala firmado es una credencial temporal de acceso a una sesión, aunque por sí solo no autoriza acciones: úsalo solo en la conversación de trabajo autorizada. El servidor no crea sesiones compartidas de forma permanente.

## 3. Registrar EcoBlend en ChatGPT

1. En ChatGPT abre **Plugins → + → Agregar servidor MCP personalizado**.
2. Nombre: `EcoBlend MCP`.
3. Conexión: pega `https://<subdominio-confirmado>.workers.dev/mcp`.
4. En esta **prueba privada**, el servidor anuncia las herramientas MCP con autenticación `Ninguna` porque el propietario controla la creación de salas con una clave, el servidor verifica la firma y caducidad de cada sala **antes** de reservar recursos, y el navegador confirma **cada** operación. **No es OAuth ni un sistema de cuentas de producción.** Si el espacio de trabajo exige OAuth, detente: hará falta implementar OAuth 2.1; no intentes eludir la política del espacio de trabajo.
5. Acepta la advertencia de seguridad y solicita detectar herramientas. Deberían aparecer `ecoblend_scene`, `ecoblend_quad_view`, `ecoblend_preset`, `ecoblend_build_blueprint`, `ecoblend_animation_preset` y otras.
6. Crea/instala la conexión y selecciónala con `@` en un nuevo chat si la plataforma lo requiere.
7. Envía el ID de sala **temporal**, no la clave privada, y pide: “Usa EcoBlend MCP, consulta mi escena en esta sala: …”. El navegador mostrará una solicitud de autorización. Revisa la acción y acepta.
8. Después prueba: “Crea una plantilla de dragón en mi sala …”. Vuelve a confirmar en EcoBlend. La figura debería aparecer y podrá exportarse a GLB desde la página.

**IMPORTANTE:** que tengas acceso a GitHub desde un chat NO conecta por sí solo las herramientas de ese MCP. El complemento debe quedar instalado/seleccionado. La opción MCP puede estar limitada por políticas y plan.

## 4. Protocolo y seguridad

- `POST /mcp`: MCP JSON-RPC 2.0, versión `2025-06-18`, transporte HTTP stateless con `initialize`, `tools/list`, `tools/call`. Solo herramientas tipadas permitidas; no expone `eval` ni ejecución remota arbitraria de JavaScript.
- `POST /pair`: solo desde el Origin oficial (o localhost de desarrollo) y con `Authorization: Bearer <ECOBLEND_PILOT_KEY>`; crea un UUID de sala firmado mediante HMAC y con caducidad de 20 minutos, más un ticket HMAC de 60 segundos para emparejar la pestaña.
- `GET /ws`: usa WSS y ticket temporal. Cada sala solo admite una pestaña; tras 20 minutos la sala caduca.
- Por cada invocación MCP, el Worker pregunta a la pestaña del propietario y espera aprobación expresa para leer o modificar.
- La clave se define como **secret** de Cloudflare, no se incluye en el código público.
- `room` figura como argumento requerido de cada herramienta. Es un identificador de prueba de tiempo limitado, no una identidad o autenticación de usuario.
- **Riesgos residuales de esta beta:** no hay OAuth, rate limiting global ni aislamiento multiusuario completo. El endpoint de herramientas es público y alguien que obtenga el UUID podría enviar solicitudes, aunque el propietario debería verlas y rechazarlas. No conectar datos confidenciales ni divulgar el UUID indiscriminadamente. Desarrollar OAuth, límites antiabuso y revocación persistente **antes de abrir el servicio al público**.
- Los datos de imágenes de referencia solo se envían cuando la persona autoriza explícitamente la herramienta correspondiente.

## 5. Test sin Cloudflare

Desde cualquier CI con Node 22 (ya incluido en GitHub Actions):

```bash
npm run check
npx wrangler@4 deploy --dry-run --config remote-mcp/wrangler.toml
```

La ejecución y empaquetado no equivalen a pruebas reales de red ni de un navegador físico. Antes de marcar “conectado con ChatGPT” deben pasar los pasos 1 a 3, comprobar la página y lograr ejecutar una herramienta desde el chat.

## 6. Próxima evolución

El piloto solo comunica la IA con la escena web ya publicada. Para liberar EcoBlend a cualquiera de forma segura hacen falta OAuth y salas asociadas a identidades, límites de uso, persistencia controlada y auditoría. El editor sigue sin modelado hiperrealista arbitrario a partir de fotos: esa capacidad requiere geometría orgánica, mejores mallas, materiales y verificación visual.
