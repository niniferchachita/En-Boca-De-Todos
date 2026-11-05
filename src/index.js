/**
 * Cloudflare Worker API para En Boca de Todos / Sistema POS
 * Base de datos: Cloudflare D1 (binding: env.DB)
 */

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status: status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Manejo de pre-flight CORS
    if (method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
      });
    }

    try {
      // -------------------------------------------------------------
      // 1. CONFIGURACIÓN GLOBAL (LOGO DEL NEGOCIO)
      // -------------------------------------------------------------
      if (path === "/api/config" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM config").all();
        const configMap = {};
        (results || []).forEach(row => {
          configMap[row.clave] = row.valor;
        });
        return jsonResponse(configMap);
      }

      if (path === "/api/config" && method === "POST") {
        const body = await request.json();
        const { clave, valor } = body;
        if (!clave) return jsonResponse({ error: "Falta la clave" }, 400);

        await env.DB.prepare(
          "INSERT INTO config (clave, valor) VALUES (?, ?) ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor"
        ).bind(clave, valor || "").run();

        return jsonResponse({ success: true });
      }

      // -------------------------------------------------------------
      // 2. CATEGORÍAS / SECCIONES
      // -------------------------------------------------------------
      if (path === "/api/categorias" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM categorias ORDER BY id ASC").all();
        return jsonResponse(results || []);
      }

      if (path === "/api/categorias" && method === "POST") {
        const body = await request.json();
        if (!body.nombre) return jsonResponse({ error: "Nombre requerido" }, 400);

        await env.DB.prepare("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)")
          .bind(body.nombre.trim())
          .run();
        return jsonResponse({ success: true });
      }

      if (path.startsWith("/api/categorias/") && method === "DELETE") {
        const id = path.split("/")[3];
        await env.DB.prepare("DELETE FROM categorias WHERE id = ?").bind(id).run();
        return jsonResponse({ success: true });
      }

      // -------------------------------------------------------------
      // 3. SALSAS Y TÉRMINOS
      // -------------------------------------------------------------
      if (path === "/api/salsas" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM salsas ORDER BY id ASC").all();
        return jsonResponse(results || []);
      }

      if (path === "/api/salsas" && method === "POST") {
        const body = await request.json();
        if (!body.nombre) return jsonResponse({ error: "Nombre requerido" }, 400);

        await env.DB.prepare("INSERT OR IGNORE INTO salsas (nombre) VALUES (?)")
          .bind(body.nombre.trim())
          .run();
        return jsonResponse({ success: true });
      }

      if (path.startsWith("/api/salsas/") && method === "DELETE") {
        const id = path.split("/")[3];
        await env.DB.prepare("DELETE FROM salsas WHERE id = ?").bind(id).run();
        return jsonResponse({ success: true });
      }

      // -------------------------------------------------------------
      // 4. USUARIOS Y ROLES PERSONALIZADOS
      // -------------------------------------------------------------
      if (path === "/api/usuarios" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT usuario, clave, nombre, rol FROM usuarios ORDER BY nombre ASC").all();
        return jsonResponse(results || []);
      }

      if (path === "/api/usuarios" && method === "POST") {
        const body = await request.json();
        const { usuario, clave, nombre, rol } = body;
        if (!usuario) return jsonResponse({ error: "Usuario requerido" }, 400);

        const u = usuario.trim();
        const n = nombre ? nombre.trim() : u;
        const r = rol ? rol.trim().toLowerCase() : "pedido";

        if (clave && clave.trim()) {
          await env.DB.prepare(
            `INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?, ?, ?)
             ON CONFLICT(usuario) DO UPDATE SET clave = excluded.clave, nombre = excluded.nombre, rol = excluded.rol`
          ).bind(u, clave.trim(), n, r).run();
        } else {
          // Actualización de datos sin sobreescribir clave si viene vacía
          await env.DB.prepare(
            `UPDATE usuarios SET nombre = ?, rol = ? WHERE usuario = ?`
          ).bind(n, r, u).run();
        }

        return jsonResponse({ success: true });
      }

      if (path.startsWith("/api/usuarios/") && method === "DELETE") {
        const u = path.split("/")[3];
        await env.DB.prepare("DELETE FROM usuarios WHERE usuario = ?").bind(decodeURIComponent(u)).run();
        return jsonResponse({ success: true });
      }

      // -------------------------------------------------------------
      // 5. PRODUCTOS / PLATOS DEL MENÚ
      // -------------------------------------------------------------
      if (path === "/api/productos" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM productos ORDER BY id DESC").all();
        return jsonResponse(results || []);
      }

      if (path === "/api/productos" && method === "POST") {
        const body = await request.json();
        const { nombre, descripcion, precio, categoria, requiere_salsa, imagen } = body;
        if (!nombre || isNaN(precio)) return jsonResponse({ error: "Datos de producto inválidos" }, 400);

        await env.DB.prepare(
          `INSERT INTO productos (nombre, descripcion, precio, categoria, requiere_salsa, imagen) 
           VALUES (?, ?, ?, ?, ?, ?)`
        ).bind(
          nombre.trim(),
          descripcion ? descripcion.trim() : "",
          parseFloat(precio),
          categoria ? categoria.trim() : "Varios",
          requiere_salsa ? 1 : 0,
          imagen || ""
        ).run();

        return jsonResponse({ success: true });
      }

      if (path.startsWith("/api/productos/") && method === "PUT") {
        const id = path.split("/")[3];
        const body = await request.json();
        const { nombre, descripcion, precio, categoria, requiere_salsa, imagen } = body;

        await env.DB.prepare(
          `UPDATE productos 
           SET nombre = ?, descripcion = ?, precio = ?, categoria = ?, requiere_salsa = ?, imagen = ? 
           WHERE id = ?`
        ).bind(
          nombre.trim(),
          descripcion ? descripcion.trim() : "",
          parseFloat(precio),
          categoria ? categoria.trim() : "Varios",
          requiere_salsa ? 1 : 0,
          imagen || "",
          id
        ).run();

        return jsonResponse({ success: true });
      }

      if (path.startsWith("/api/productos/") && method === "DELETE") {
        const id = path.split("/")[3];
        await env.DB.prepare("DELETE FROM productos WHERE id = ?").bind(id).run();
        return jsonResponse({ success: true });
      }

      // -------------------------------------------------------------
      // 6. PEDIDOS (CONSULTAR, CREAR, ACTUALIZAR Y ELIMINAR)
      // -------------------------------------------------------------
      if (path === "/api/pedidos" && method === "GET") {
        const { results } = await env.DB.prepare("SELECT * FROM pedidos ORDER BY id DESC").all();
        return jsonResponse(results || []);
      }

      if (path === "/api/pedidos" && method === "POST") {
        const body = await request.json();
        const {
          cliente,
          fact_ruc,
          fact_razon,
          fact_dir,
          fact_phone,
          fact_email,
          items,
          total,
          estado,
          mesero,
          metodo_pago,
          fecha_hora
        } = body;

        const result = await env.DB.prepare(
          `INSERT INTO pedidos 
           (cliente, fact_ruc, fact_razon, fact_dir, fact_phone, fact_email, items, total, estado, mesero, metodo_pago, fecha_hora)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
        ).bind(
          cliente || "Cliente General",
          fact_ruc || "Consumidor Final",
          fact_razon || cliente || "Consumidor Final",
          fact_dir || "N/A",
          fact_phone || "N/A",
          fact_email || "N/A",
          typeof items === "string" ? items : JSON.stringify(items || []),
          parseFloat(total) || 0,
          estado || "pendiente",
          mesero || "Sistema",
          metodo_pago || "Efectivo",
          fecha_hora || new Date().toISOString()
        ).run();

        return jsonResponse({ success: true, id: result.meta?.last_row_id });
      }

      if (path.startsWith("/api/pedidos/") && method === "PUT") {
        const id = path.split("/")[3];
        const body = await request.json();

        // 1. Modificación de ítems y total (Edición desde Caja)
        if (body.items !== undefined && body.total !== undefined) {
          await env.DB.prepare(
            `UPDATE pedidos SET items = ?, total = ? WHERE id = ?`
          ).bind(
            typeof body.items === "string" ? body.items : JSON.stringify(body.items),
            parseFloat(body.total),
            id
          ).run();
          return jsonResponse({ success: true });
        }

        // 2. Liquidación / Cobro con método de pago
        if (body.estado === "cobrado" && body.metodo_pago) {
          await env.DB.prepare(
            `UPDATE pedidos SET estado = 'cobrado', metodo_pago = ? WHERE id = ?`
          ).bind(body.metodo_pago, id).run();
          return jsonResponse({ success: true });
        }

        // 3. Cambio de estado general (listo en cocina, anulado, etc.)
        if (body.estado) {
          await env.DB.prepare(
            `UPDATE pedidos SET estado = ? WHERE id = ?`
          ).bind(body.estado, id).run();
          return jsonResponse({ success: true });
        }

        return jsonResponse({ error: "Sin datos para actualizar" }, 400);
      }

      // ELIMINAR PEDIDO DEFINITIVAMENTE DE LA BASE DE DATOS
      if (path.startsWith("/api/pedidos/") && method === "DELETE") {
        const id = path.split("/")[3];
        await env.DB.prepare("DELETE FROM pedidos WHERE id = ?").bind(id).run();
        return jsonResponse({ success: true, message: `Pedido #${id} eliminado` });
      }

      return jsonResponse({ error: "Ruta no encontrada" }, 404);

    } catch (err) {
      return jsonResponse({ error: err.message || "Error interno del servidor" }, 500);
    }
  }
};