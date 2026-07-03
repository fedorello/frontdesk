// The Privacy Policy in every service language. Server components pick by the language cookie.
import type { Locale } from "../locales";

const en = `# Privacy Policy

_Last updated: 27 June 2026_

> **In short:** To run your AI front desk, we store your business settings and the
> **conversations** between your bot and your customers on our servers — that's how the
> assistant remembers context and books appointments. You can **delete your account and
> everything in it at any time**, permanently.

This policy covers the **hosted service at tovayo.com**. If you self-host the open-source
code, you run your own database and this policy does not apply — you are the data controller.

## 1. What we store

- **Account data** — your email and a hashed password.
- **Business profile** — name, owner name, time zone, description, address / online flag,
  services, working hours, FAQ, and your chosen language.
- **Connection secrets** — your Telegram bot token and (optional) your own AI API key,
  **encrypted at rest**.
- **Customers** — for each person who messages your bot: their channel id, display name (if
  the channel provides one), and language.
- **Conversations** — the full message history between your bot, your customers, the AI
  assistant, and you, stored so the assistant has context across messages.
- **Bookings** — appointments and the intake answers you configured to collect, plus reminders.
- **Operational counters** — minimal usage counts for cost control and diagnostics.

We do **not** sell your data, and we do **not** use your conversations to train our own models.

## 2. Why we store it

Solely to operate the Service for you: answer customers, schedule and remind, give you a
dashboard, prevent abuse, and keep the system running.

## 3. Who else processes it

To function, message content and related data are shared with an **AI model provider** (to
generate replies), your **messaging channel** (e.g. Telegram), and our **hosting provider**
(where the servers and database run). These act as processors for running the Service.

## 4. How long we keep it

We keep your data while your account is active. **When you delete your account, we permanently
erase your business and all associated records** — conversations, customers, bookings,
services, settings, and connection secrets — in one irreversible operation.

## 5. Your choices and rights

- **Delete everything, anytime.** Settings → *Danger zone* → *Delete account* removes your
  account and all its data, permanently. There is no undo.
- **Access / correction.** You can view and edit your business data in the dashboard at any time.
- Depending on where you live, you may have additional rights (access, erasure, portability,
  objection). Contact us to exercise them.

## 6. Your customers' data

Your customers' messages and details are data **you** bring into the Service. You are
responsible for having a lawful basis to process them (see the [Terms](/terms), §5). When you
delete your account, their data tied to your business is deleted too.

## 7. Security

Secrets (bot tokens, API keys) are encrypted at rest, and access is restricted to the running
Service. No system is perfectly secure, but we take reasonable measures to protect your data.

## 8. Children

The Service is for businesses and is not directed at children. Don't use it to collect data
from children unlawfully.

## 9. Changes

We may update this policy; material changes will be announced in-product or on tovayo.com.

## 10. Contact

Privacy questions or requests: **privacy@tovayo.com**.`;

const ru = `# Политика конфиденциальности

_Обновлено: 27 июня 2026_

> **Коротко:** Чтобы ваш ИИ-ресепшн работал, мы храним на своих серверах настройки вашего
> бизнеса и **переписку** между вашим ботом и вашими клиентами — именно так ассистент
> помнит контекст и записывает на приём. Вы можете **удалить свой аккаунт и всё, что в нём
> есть, в любой момент**, безвозвратно.

Эта политика распространяется на **облачный сервис на tovayo.com**. Если вы разворачиваете
open-source-код самостоятельно, вы используете собственную базу данных, и эта политика на вас
не распространяется — оператором данных являетесь вы.

## 1. Что мы храним

- **Данные аккаунта** — ваш email и хэшированный пароль.
- **Профиль бизнеса** — название, имя владельца, часовой пояс, описание, адрес / отметка о
  работе онлайн, услуги, часы работы, FAQ и выбранный вами язык.
- **Секреты подключения** — токен вашего Telegram-бота и (по желанию) ваш собственный ключ
  API для ИИ, **зашифрованные при хранении**.
- **Клиенты** — по каждому, кто пишет вашему боту: его идентификатор в канале, отображаемое
  имя (если канал его предоставляет) и язык.
- **Переписка** — полная история сообщений между вашим ботом, вашими клиентами, ИИ-ассистентом
  и вами, которая хранится, чтобы у ассистента был контекст между сообщениями.
- **Записи на приём** — встречи и ответы на вопросы анкеты, которые вы настроили собирать, а
  также напоминания.
- **Операционные счётчики** — минимальные показатели использования для контроля расходов и
  диагностики.

Мы **не** продаём ваши данные и **не** используем вашу переписку для обучения собственных моделей.

## 2. Зачем мы это храним

Исключительно для того, чтобы предоставлять вам Сервис: отвечать клиентам, вести запись и
напоминать о встречах, давать вам панель управления, предотвращать злоупотребления и
поддерживать работу системы.

## 3. Кто ещё обрабатывает эти данные

Для работы Сервиса содержимое сообщений и связанные с ним данные передаются **провайдеру
ИИ-модели** (чтобы формировать ответы), вашему **каналу связи** (например, Telegram) и нашему
**хостинг-провайдеру** (где работают серверы и база данных). Они выступают обработчиками
данных для обеспечения работы Сервиса.

## 4. Как долго мы это храним

Мы храним ваши данные, пока ваш аккаунт активен. **Когда вы удаляете аккаунт, мы безвозвратно
стираем ваш бизнес и все связанные с ним записи** — переписку, клиентов, записи на приём,
услуги, настройки и секреты подключения — одной необратимой операцией.

## 5. Ваш выбор и права

- **Удалить всё, в любой момент.** Настройки → *Опасная зона* → *Удалить аккаунт* — удаляет
  ваш аккаунт и все его данные, безвозвратно. Отменить это нельзя.
- **Доступ / исправление.** Вы можете просматривать и редактировать данные своего бизнеса в
  панели управления в любое время.
- В зависимости от страны проживания у вас могут быть дополнительные права (доступ, удаление,
  переносимость, возражение). Свяжитесь с нами, чтобы ими воспользоваться.

## 6. Данные ваших клиентов

Сообщения и данные ваших клиентов — это данные, которые **вы** привносите в Сервис. Вы
отвечаете за наличие законного основания для их обработки (см. [Условия](/terms), §5). Когда
вы удаляете аккаунт, их данные, связанные с вашим бизнесом, также удаляются.

## 7. Безопасность

Секреты (токены ботов, ключи API) шифруются при хранении, а доступ к ним ограничен работающим
Сервисом. Ни одна система не является идеально защищённой, но мы принимаем разумные меры для
защиты ваших данных.

## 8. Дети

Сервис предназначен для бизнеса и не ориентирован на детей. Не используйте его для незаконного
сбора данных о детях.

## 9. Изменения

Мы можем обновлять эту политику; о существенных изменениях мы сообщим в самом продукте или на
tovayo.com.

## 10. Контакты

Вопросы или запросы по конфиденциальности: **privacy@tovayo.com**.`;

const es = `# Política de Privacidad

_Última actualización: 27 de junio de 2026_

> **En resumen:** Para gestionar tu recepción con IA, almacenamos en nuestros servidores la
> configuración de tu negocio y las **conversaciones** entre tu bot y tus clientes: así es como el
> asistente recuerda el contexto y agenda las citas. Puedes **eliminar tu cuenta y todo lo que
> contiene en cualquier momento**, de forma permanente.

Esta política cubre el **servicio alojado en tovayo.com**. Si alojas por tu cuenta el código de
código abierto, tú operas tu propia base de datos y esta política no aplica: tú eres el responsable
del tratamiento de los datos.

## 1. Qué almacenamos

- **Datos de la cuenta**: tu correo electrónico y una contraseña cifrada (hash).
- **Perfil del negocio**: nombre, nombre del propietario, zona horaria, descripción, dirección /
  indicador de negocio en línea, servicios, horario de atención, preguntas frecuentes y el idioma
  que elijas.
- **Secretos de conexión**: el token de tu bot de Telegram y (opcionalmente) tu propia clave de API
  de IA, **cifrados en reposo**.
- **Clientes**: para cada persona que escribe a tu bot: su identificador de canal, nombre visible (si
  el canal lo proporciona) e idioma.
- **Conversaciones**: el historial completo de mensajes entre tu bot, tus clientes, el asistente de IA
  y tú, almacenado para que el asistente tenga contexto a lo largo de los mensajes.
- **Reservas**: citas y las respuestas de admisión que configuraste para recopilar, además de los recordatorios.
- **Contadores operativos**: recuentos mínimos de uso para el control de costos y el diagnóstico.

**No** vendemos tus datos y **no** usamos tus conversaciones para entrenar nuestros propios modelos.

## 2. Por qué lo almacenamos

Únicamente para operar el Servicio para ti: responder a los clientes, agendar y enviar recordatorios,
ofrecerte un panel de control, prevenir el abuso y mantener el sistema en funcionamiento.

## 3. Quién más lo procesa

Para funcionar, el contenido de los mensajes y los datos relacionados se comparten con un **proveedor
de modelos de IA** (para generar respuestas), tu **canal de mensajería** (por ejemplo, Telegram) y
nuestro **proveedor de alojamiento** (donde se ejecutan los servidores y la base de datos). Estos
actúan como encargados del tratamiento para el funcionamiento del Servicio.

## 4. Cuánto tiempo lo conservamos

Conservamos tus datos mientras tu cuenta esté activa. **Cuando eliminas tu cuenta, borramos de forma
permanente tu negocio y todos los registros asociados** —conversaciones, clientes, reservas,
servicios, configuración y secretos de conexión— en una sola operación irreversible.

## 5. Tus opciones y derechos

- **Elimina todo, en cualquier momento.** Configuración → *Zona de peligro* → *Eliminar cuenta*
  elimina tu cuenta y todos sus datos, de forma permanente. No hay forma de deshacerlo.
- **Acceso / corrección.** Puedes ver y editar los datos de tu negocio en el panel de control en
  cualquier momento.
- Según el lugar donde residas, puedes tener derechos adicionales (acceso, supresión, portabilidad,
  oposición). Contáctanos para ejercerlos.

## 6. Los datos de tus clientes

Los mensajes y los datos de tus clientes son datos que **tú** aportas al Servicio. Eres responsable de
contar con una base legal para tratarlos (consulta los [Términos](/terms), §5). Cuando eliminas tu
cuenta, sus datos vinculados a tu negocio también se eliminan.

## 7. Seguridad

Los secretos (tokens de bots, claves de API) se cifran en reposo, y el acceso está restringido al
Servicio en ejecución. Ningún sistema es perfectamente seguro, pero tomamos medidas razonables para
proteger tus datos.

## 8. Menores

El Servicio está dirigido a negocios y no está destinado a menores. No lo utilices para recopilar
datos de menores de forma ilícita.

## 9. Cambios

Podemos actualizar esta política; los cambios sustanciales se anunciarán dentro del producto o en
tovayo.com.

## 10. Contacto

Consultas o solicitudes sobre privacidad: **privacy@tovayo.com**.`;

const zh = `# 隐私政策

_最后更新：2026 年 6 月 27 日_

> **简而言之：** 为了运行您的 AI 前台，我们会在我们的服务器上存储您的业务设置以及您的机器人与客户之间的**对话**——助手正是借此记住上下文并预约。您可以**随时永久删除您的账户及其中的所有内容**。

本政策适用于 **tovayo.com 上的托管服务**。如果您自行托管这套开源代码，则由您运行自己的数据库，本政策不适用——您即为数据控制者。

## 1. 我们存储哪些内容

- **账户数据**——您的电子邮箱和经哈希处理的密码。
- **业务资料**——名称、所有者姓名、时区、简介、地址／线上标识、服务项目、营业时间、常见问题解答，以及您选择的语言。
- **连接密钥**——您的 Telegram 机器人令牌以及（可选的）您自己的 AI API 密钥，**均加密存储**。
- **客户**——针对每一位向您的机器人发送消息的人：其渠道 id、显示名称（如渠道提供）以及语言。
- **对话**——您的机器人、您的客户、AI 助手与您之间的完整消息记录，予以存储，以便助手在多条消息之间保有上下文。
- **预约**——预约信息以及您配置收集的登记问题答案，还有提醒。
- **运营计数器**——用于成本控制和诊断的最小化使用计数。

我们**不会**出售您的数据，也**不会**使用您的对话来训练我们自己的模型。

## 2. 我们为何存储

仅为向您运营本服务：答复客户、安排日程与提醒、为您提供仪表盘、防止滥用，并保持系统正常运行。

## 3. 还有谁会处理这些数据

为实现功能，消息内容及相关数据会与 **AI 模型提供方**（用于生成回复）、您的**消息渠道**（例如 Telegram）以及我们的**托管服务提供方**（服务器与数据库的运行所在）共享。这些方作为运行本服务的处理者。

## 4. 我们保留数据多久

在您的账户处于活跃状态期间，我们会保留您的数据。**当您删除账户时，我们会永久抹除您的业务及所有相关记录**——对话、客户、预约、服务项目、设置以及连接密钥——通过一次不可逆的操作完成。

## 5. 您的选择与权利

- **随时删除全部内容。** 设置 →*危险区域*→*删除账户*，即可永久移除您的账户及其全部数据。此操作无法撤销。
- **访问／更正。** 您可以随时在仪表盘中查看和编辑您的业务数据。
- 视您所在地区而定，您可能享有额外权利（访问、删除、可携带、反对）。请联系我们以行使这些权利。

## 6. 您客户的数据

您客户的消息与详情是**您**带入本服务的数据。您有责任确保拥有处理这些数据的合法依据（参见 [服务条款](/terms)，§5）。当您删除账户时，与您业务相关联的客户数据也会一并删除。

## 7. 安全

密钥（机器人令牌、API 密钥）加密存储，访问权限仅限于正在运行的服务。没有任何系统是绝对安全的，但我们会采取合理措施来保护您的数据。

## 8. 儿童

本服务面向企业，并非针对儿童。请勿使用本服务非法收集儿童数据。

## 9. 变更

我们可能会更新本政策；重大变更将在产品内或 tovayo.com 上予以公告。

## 10. 联系方式

隐私相关问题或请求：**privacy@tovayo.com**。`;

export const PRIVACY: Record<Locale, string> = { en, ru, es, zh };
